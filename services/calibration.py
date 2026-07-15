import statistics
from dao.task_dao import get_category_history, get_all_done_history, get_recent_ratios_by_category
from dao.settings_dao import get_setting
from utils.db import get_current_user_id


class CalibrationEngine:
    """
    校准引擎 — 支持多种策略计算膨胀系数。
    策略：median / mean / weighted_recent / ml_basic
    """

    STRATEGIES = ["median", "mean", "weighted_recent", "ml_basic"]

    def __init__(self, user_id=None):
        self.user_id = user_id if user_id is not None else get_current_user_id()
        self._strategy = None

    @property
    def strategy(self):
        if self._strategy is None:
            self._strategy = get_setting("calibration_strategy", "median", self.user_id)
            if self._strategy not in self.STRATEGIES:
                self._strategy = "median"
        return self._strategy

    @strategy.setter
    def strategy(self, value):
        if value not in self.STRATEGIES:
            raise ValueError(f"Invalid strategy: {value}. Choose from {self.STRATEGIES}")
        self._strategy = value

    def get_expansion_ratio(self, category: str) -> float:
        methods = {
            "median": self._median_ratio,
            "mean": self._mean_ratio,
            "weighted_recent": self._weighted_recent_ratio,
            "ml_basic": self._ml_basic_ratio,
        }
        method = methods.get(self.strategy, self._median_ratio)
        return method(category)

    def _get_ratios(self, category: str) -> list[float]:
        rows = get_category_history(category, self.user_id)
        if len(rows) < 3:
            rows = get_all_done_history(self.user_id)
        ratios = []
        for r in rows:
            est = r['estimated_minutes']
            act = r['actual_minutes']
            if est and act and est > 0:
                ratios.append(act / est)
        return ratios

    def _median_ratio(self, category: str) -> float:
        ratios = self._get_ratios(category)
        if not ratios:
            return 1.0
        return round(statistics.median(ratios), 2)

    def _mean_ratio(self, category: str) -> float:
        ratios = self._get_ratios(category)
        if not ratios:
            return 1.0
        return round(statistics.mean(ratios), 2)

    def _weighted_recent_ratio(self, category: str) -> float:
        """
        加权近期策略：近期任务权重更高。
        使用指数衰减：w_i = exp(-λ * i)，i 为距今天数（0=今天）。
        """
        recent = get_recent_ratios_by_category(category, self.user_id, limit=20)
        if not recent:
            return self._median_ratio(category)

        from datetime import date
        today = date.today()
        weighted_sum = 0.0
        total_weight = 0.0
        lam = 0.1

        for i, r in enumerate(recent):
            ratio = r['ratio']
            if ratio is None or ratio <= 0:
                continue
            try:
                task_date = date.fromisoformat(r['created_date'])
                days_ago = (today - task_date).days
            except (ValueError, TypeError):
                days_ago = i
            weight = 2.71828 ** (-lam * days_ago)
            weighted_sum += ratio * weight
            total_weight += weight

        if total_weight == 0:
            return 1.0
        return round(weighted_sum / total_weight, 2)

    def _ml_basic_ratio(self, category: str) -> float:
        """
        基础 ML 策略：使用简单线性回归拟合「估计时间 → 实际时间」。
        数据不足时自动回退到中位数策略。
        """
        rows = get_category_history(category, self.user_id)
        if len(rows) < 5:
            rows = get_all_done_history(self.user_id)
        if len(rows) < 5:
            return self._median_ratio(category)

        xs = [r['estimated_minutes'] for r in rows if r['actual_minutes'] and r['estimated_minutes'] > 0]
        ys = [r['actual_minutes'] for r in rows if r['actual_minutes'] and r['estimated_minutes'] > 0]
        if len(xs) < 5:
            return self._median_ratio(category)

        n = len(xs)
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 1.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        avg_x = sum_x / n
        if avg_x == 0:
            return 1.0
        predicted = slope * avg_x + intercept
        ratio = predicted / avg_x
        return round(max(ratio, 0.5), 2)

    def calibrate_task(self, task: dict) -> tuple[float, int]:
        category = task.get('category', '')
        if not category:
            return 1.0, task['estimated_minutes']
        ratio = self.get_expansion_ratio(category)
        calibrated = int(task['estimated_minutes'] * ratio)
        return ratio, calibrated

    def calibrate_all_tasks(self, tasks: list[dict]) -> list[dict]:
        results = []
        for task in tasks:
            ratio, calibrated = self.calibrate_task(task)
            results.append({
                **task,
                'expansion_ratio': ratio,
                'calibrated_minutes': calibrated
            })
        return results

    def get_strategy_info(self) -> dict:
        return {
            "current": self.strategy,
            "available": self.STRATEGIES,
            "descriptions": {
                "median": "中位数：取历史比值中位数，抗极端值干扰，最稳健",
                "mean": "均值：取历史比值平均值，受极端值影响较大",
                "weighted_recent": "加权近期：近期任务权重更高，适合时间感知在变化的人",
                "ml_basic": "基础 ML：简单线性回归拟合估计→实际关系，数据越多越准",
            }
        }


_engine_cache = {}
_MAX_CACHE_SIZE = 50


def clear_engine_cache(user_id=None):
    if user_id is not None:
        _engine_cache.pop(user_id, None)
    else:
        _engine_cache.clear()


def get_engine(user_id=None) -> CalibrationEngine:
    if user_id is None:
        user_id = get_current_user_id()
    if user_id not in _engine_cache:
        if len(_engine_cache) >= _MAX_CACHE_SIZE:
            _engine_cache.pop(next(iter(_engine_cache)))
        _engine_cache[user_id] = CalibrationEngine(user_id)
    return _engine_cache[user_id]


def get_category_expansion_ratio(category, user_id=None):
    return get_engine(user_id).get_expansion_ratio(category)


def get_calibration_info(category, user_id=None):
    engine = get_engine(user_id)
    ratios = engine._get_ratios(category)
    ratio = engine.get_expansion_ratio(category)
    return {
        "ratio": ratio,
        "sample_count": len(ratios),
        "strategy": engine.strategy,
        "has_data": len(ratios) > 0,
    }


def calibrate_task(task, user_id=None):
    return get_engine(user_id).calibrate_task(task)


def calibrate_all_tasks(tasks, user_id=None):
    return get_engine(user_id).calibrate_all_tasks(tasks)


def calibrate_all_tasks_with_info(tasks, user_id=None):
    engine = get_engine(user_id)
    results = engine.calibrate_all_tasks(tasks)
    for task, result in zip(tasks, results):
        ratios = engine._get_ratios(task['category'])
        result['calibration_sample_count'] = len(ratios)
    return results