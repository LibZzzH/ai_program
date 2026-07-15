import streamlit as st
from datetime import datetime
from services.task_manager import get_today_tasks
from dao.task_dao import update_task_status, set_actual_minutes


def render_floating_timer():
    if not st.session_state.timer_running:
        return

    task_id = st.session_state.timer_task_id
    today_tasks = get_today_tasks()
    current_task = next((t for t in today_tasks if t['id'] == task_id), None)

    if current_task is None:
        st.session_state.timer_running = False
        st.session_state.timer_task_id = None
        st.session_state.timer_start = None
        st.session_state.timer_elapsed_seconds = 0
        st.rerun()

    start_ts = int(st.session_state.timer_start.timestamp() * 1000)
    est_minutes = current_task['estimated_minutes']
    task_name = current_task['description'][:30]
    task_category = current_task['category']

    timer_html = f"""<!DOCTYPE html>
<html><head>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;font-family:'Inter','Noto Sans SC',sans-serif;overflow:hidden;}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 6px rgba(82,183,136,0.3);}}50%{{box-shadow:0 0 16px rgba(82,183,136,0.7);}}}}
@keyframes pulse-red{{0%,100%{{box-shadow:0 0 6px rgba(230,57,70,0.3);}}50%{{box-shadow:0 0 16px rgba(230,57,70,0.7);}}}}
.timer-bar{{display:flex;align-items:center;justify-content:space-between;background:var(--timer-bg,#FFFFFF);border:2px solid var(--timer-clock,#52B788);border-radius:14px;padding:10px 20px;animation:pulse 2s infinite;gap:16px;box-shadow:0 2px 12px rgba(0,0,0,0.04);}}
.timer-bar.overtime{{border-color:var(--timer-overtime-border,#E63946);animation:pulse-red 1s infinite;background:var(--timer-overtime-bg,#FFF5F5);}}
.timer-left{{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1;}}
.timer-name{{color:var(--timer-text,#2D2D2D);font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.timer-meta{{color:var(--timer-meta,#8E8E8E);font-size:11px;}}
.timer-right{{display:flex;align-items:center;gap:12px;flex-shrink:0;}}
.timer-clock{{font-family:'JetBrains Mono','Courier New',monospace;font-size:36px;font-weight:700;color:var(--timer-clock,#52B788);letter-spacing:2px;min-width:150px;text-align:center;}}
.timer-clock.overtime{{color:var(--timer-overtime-clock,#E63946);}}
.timer-dot{{width:8px;height:8px;border-radius:50%;background:var(--timer-clock,#52B788);}}
.timer-dot.overtime{{background:var(--timer-overtime-clock,#E63946);}}
.timer-live{{color:var(--timer-clock,#52B788);font-size:11px;font-weight:600;}}
.timer-live.overtime{{color:var(--timer-overtime-clock,#E63946);}}
.timer-progress-wrap{{padding:6px 20px 0 20px;display:flex;align-items:center;gap:8px;}}
.timer-progress-label{{font-size:11px;color:var(--timer-progress-label,#8E8E8E);white-space:nowrap;}}
.timer-progress-bar{{flex:1;height:5px;background:var(--timer-progress-bg,#E2E8F0);border-radius:3px;overflow:hidden;}}
.timer-progress-fill{{height:5px;background:var(--timer-progress-fill,#52B788);border-radius:3px;transition:width 0.3s;}}
.timer-progress-fill.overtime{{background:var(--timer-overtime-clock,#E63946);}}
</style></head>
<body>
<div class="timer-bar" id="bar">
<div class="timer-left"><div class="timer-name">🔄 {task_name}</div><div class="timer-meta" id="meta">{task_category} · 估计 {est_minutes} 分钟</div></div>
<div class="timer-right"><div class="timer-clock" id="clock">00:00:00</div><span class="timer-dot" id="dot"></span><span class="timer-live" id="live">计时中</span></div>
</div>
<div class="timer-progress-wrap">
<span class="timer-progress-label" id="progLabel">已用 0min / 预估 {est_minutes}min</span>
<div class="timer-progress-bar"><div class="timer-progress-fill" id="progFill" style="width:0%"></div></div>
</div>
<script>
var startTime={start_ts},estSeconds={est_minutes}*60;
var clockEl=document.getElementById('clock'),barEl=document.getElementById('bar'),dotEl=document.getElementById('dot'),liveEl=document.getElementById('live'),metaEl=document.getElementById('meta'),progLabel=document.getElementById('progLabel'),progFill=document.getElementById('progFill');
function pad(n){{return String(n).padStart(2,'0');}}
function tick(){{var e=Math.floor((Date.now()-startTime)/1000);var em=Math.floor(e/60);clockEl.textContent=pad(Math.floor(e/3600))+':'+pad(Math.floor((e%3600)/60))+':'+pad(e%60);
var pct=Math.min(e/estSeconds*100,100);
progFill.style.width=pct+'%';progLabel.textContent='已用 '+em+'min / 预估 {est_minutes}min';
if(e>estSeconds){{clockEl.className='timer-clock overtime';barEl.className='timer-bar overtime';dotEl.className='timer-dot overtime';liveEl.className='timer-live overtime';liveEl.textContent='超时 '+(e/estSeconds).toFixed(1)+'x';progFill.className='timer-progress-fill overtime';progFill.style.width='100%';}}
else{{clockEl.className='timer-clock';barEl.className='timer-bar';dotEl.className='timer-dot';liveEl.className='timer-live';liveEl.textContent='计时中';progFill.className='timer-progress-fill';}}}}
tick();setInterval(tick,200);
</script></body></html>"""

    st.components.v1.html(timer_html, height=100, scrolling=False)

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("⏹️ 完成计时", type="primary", use_container_width=True, key="float_finish_btn"):
            finish_task_from_timer(task_id)
            st.rerun()
    with col2:
        if st.button("⏸️ 暂停", use_container_width=True, key="float_pause_btn"):
            st.session_state.timer_running = False
            st.session_state.last_tick = None
            st.rerun()


def finish_task_from_timer(task_id):
    end_time = datetime.now()
    update_task_status(task_id, 'done', end_time=end_time.isoformat())
    elapsed = (end_time - st.session_state.timer_start).total_seconds() / 60
    set_actual_minutes(task_id, int(elapsed))
    st.session_state.timer_running = False
    st.session_state.timer_task_id = None
    st.session_state.timer_start = None
    st.session_state.timer_elapsed_seconds = 0
    st.session_state.show_actual_input = True
    st.session_state.actual_task_id = task_id
    st.session_state.elapsed_minutes = int(elapsed)