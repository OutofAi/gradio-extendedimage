import gradio as gr
from gradio_extendedimage import extendedimage

def on_stroke(evt: gr.EventData):
    detail = getattr(evt, "data", None) or getattr(evt, "_data", {}) or {}
    points = detail.get("points", [])
    done = detail.get("done", False)
    return f"{len(points)} points, done={done}"

def internal_fn(evt: gr.EventData):
    detail = getattr(evt, "data", None) or getattr(evt, "_data", {}) or {}
    return detail['value']


with gr.Blocks() as demo:
    img = extendedimage(selectable=True)
    out = gr.Textbox()
    orientation = gr.Textbox()
    img.stroke(fn=on_stroke, outputs=out)
    img.orientation(fn=internal_fn, outputs=[orientation])

if __name__ == '__main__':
    demo.launch()


