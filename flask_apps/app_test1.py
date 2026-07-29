from flask import Flask, render_template, jsonify, request
import threading
import asyncio

app = Flask(__name__)

server_status = {'status': 'idle'}
job_thread = {'thread': None}
job_stop_flag = {'stop': False}

# ----------------------
# Async job definitions
# ----------------------
async def async_task(name, delay):
    print(f"Start {name}")
    await asyncio.sleep(delay)
    print(f"Finish {name}")

async def run_all_tasks():
    tasks = [
        async_task("Task A", 3),
        async_task("Task B", 2),
        async_task("Task C", 1),
    ]
    await asyncio.gather(*tasks)

def background_worker():
    global server_status, job_stop_flag
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    server_status['status'] = 'running'
    job_stop_flag['stop'] = False
    try:
        async def monitored_run():
            task = asyncio.create_task(run_all_tasks())
            while not task.done():
                if job_stop_flag['stop']:
                    print("Stop signal received")
                    task.cancel()
                    break
                await asyncio.sleep(0.2)
            try:
                await task
            except asyncio.CancelledError:
                print("Task cancelled")

        loop.run_until_complete(monitored_run())
    finally:
        server_status['status'] = 'idle'
        loop.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def Run():
    if server_status['status'] == 'idle':
        t = threading.Thread(target=background_worker)
        t.start()
        job_thread['thread'] = t
    return '', 204

@app.route('/stop', methods=['POST'])
def Stop():
    job_stop_flag['stop'] = True
    return '', 204

@app.route('/status')
def status():
    return jsonify(server_status)

if __name__ == '__main__':
    app.run(debug=True)
