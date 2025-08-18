
import gradio as gr
from gradio_extendedimage import extendedimage


example = extendedimage().example_value()

demo = gr.Interface(
    lambda x:x,
    extendedimage(),  # interactive version of your component
    extendedimage(),  # static version of your component
    # examples=[[example]],  # uncomment this line to view the "example version" of your component
)


if __name__ == "__main__":
    demo.launch()
