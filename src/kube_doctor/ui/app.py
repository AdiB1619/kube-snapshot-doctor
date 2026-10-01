"""Optional Gradio front end.

Install with the extra: ``pip install -e ".[ui]"``. This module calls
:func:`kube_doctor.pipeline.run` and does nothing else, so the CLI, the Agent
Skill, and the eval harness keep exactly one implementation of the pipeline.
"""

from __future__ import annotations

import logging

import gradio as gr

from kube_doctor.backends.base import BackendError
from kube_doctor.backends.factory import build_backend
from kube_doctor.pipeline import InputError, ModelOutputError, PipelineResult, run
from kube_doctor.render import result_to_markdown

logger = logging.getLogger(__name__)

#: Backends offered in the dropdown, in the order they should be tried.
BACKEND_CHOICES = ["gemini", "openai-compat"]


def diagnose(
    image: object,
    logs: str | None,
    namespace: str | None,
    context: str | None,
    backend_name: str,
) -> str:
    """Run the pipeline and return Markdown, or an error message to display."""
    if image is None:
        return "Upload a screenshot, or paste logs, before running the diagnosis."
    try:
        backend: object = build_backend(backend_name or BACKEND_CHOICES[0])
    except BackendError as exc:
        return f"**Backend error:** {exc}\n\nSet the model and credentials, then try again."
    try:
        result: PipelineResult = run(
            image,  # type: ignore[arg-type]
            backend,  # type: ignore[arg-type]
            logs_text=logs or None,
            namespace=namespace or "",
            context=context or "",
        )
    except InputError as exc:
        return f"**Bad input:** {exc}"
    except ModelOutputError as exc:
        return f"**The model's output could not be repaired:** {exc}"
    except BackendError as exc:
        return f"**Backend error:** {exc}"
    return result_to_markdown(result)


def build_app() -> gr.Blocks:
    """Build the Gradio app."""
    with gr.Blocks(title="Kube Snapshot Doctor", theme=gr.themes.Soft()) as app:
        gr.Markdown(
            "# Kube Snapshot Doctor\n"
            "Diagnose a Kubernetes problem from a screenshot. "
            "Nothing here connects to a cluster and nothing is executed."
        )
        with gr.Row():
            with gr.Column():
                image_input = gr.Image(
                    type="filepath",
                    label="Screenshot",
                    sources=["upload", "clipboard"],
                )
                logs_input = gr.Textbox(
                    label="Logs (optional)",
                    lines=10,
                    placeholder="kubectl logs <pod> --previous --tail=200",
                )
                with gr.Row():
                    namespace_input = gr.Textbox(label="Namespace (optional)", scale=1)
                    backend_input = gr.Dropdown(
                        label="Backend",
                        choices=BACKEND_CHOICES,
                        value=BACKEND_CHOICES[0],
                        scale=1,
                    )
                context_input = gr.Textbox(
                    label="Context (optional)",
                    lines=3,
                    placeholder="What changed? What have you already tried?",
                )
                run_button = gr.Button("Diagnose", variant="primary")
            with gr.Column():
                output = gr.Markdown(label="Diagnosis")
        run_button.click(
            fn=diagnose,
            inputs=[image_input, logs_input, namespace_input, context_input, backend_input],
            outputs=output,
        )
    return app


def main() -> None:
    """Launch the app."""
    logging.basicConfig(level=logging.WARNING)
    build_app().launch()


if __name__ == "__main__":  # pragma: no cover
    main()
