
import gradio as gr
from gradio_extendedimage import extendedimage



def internal_fn(evt: gr.EventData):
    detail = getattr(evt, "data", None) or getattr(evt, "_data", {}) or {}
    return detail['value']

with gr.Blocks() as demo:
    src = extendedimage()
    out = gr.Text()
    src.orientation(fn=internal_fn, outputs=[out])

if __name__ == "__main__":
    demo.launch()
