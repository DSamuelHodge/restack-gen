"""Template rendering engine for restack-gen.

This module provides utilities for rendering Jinja2 templates with common context
and proper timestamp generation.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from restack_gen import __version__


class TemplateRenderer:
    """Renders Jinja2 templates with common context."""

    def __init__(self) -> None:
        """Initialize the template renderer with Jinja2 environment."""
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render_template(self, template_name: str, context: dict[str, Any] | None = None) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of the template file (e.g., 'agent.py.j2')
            context: Template variables to pass to the template

        Returns:
            Rendered template as a string
        """
        template = self.env.get_template(template_name)
        full_context = self._build_context(context or {})
        return template.render(**full_context)

    def _build_context(self, user_context: dict[str, Any]) -> dict[str, Any]:
        """Build the full template context with common variables.

        Args:
            user_context: User-provided template variables

        Returns:
            Complete context dictionary with common variables added
        """
        common_context = {
            "generator_version": __version__,
            "timestamp": self._get_timestamp(),
        }
        # User context takes precedence over common context
        return {**common_context, **user_context}

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format.

        Returns:
            ISO 8601 formatted timestamp string
        """
        return datetime.now(UTC).isoformat()


# Singleton instance for convenience
_renderer = TemplateRenderer()


def render_template(template_name: str, context: dict[str, Any] | None = None) -> str:
    """Convenience function to render a template.

    Args:
        template_name: Name of the template file (e.g., 'agent.py.j2')
        context: Template variables to pass to the template

    Returns:
        Rendered template as a string
    """
    return _renderer.render_template(template_name, context)
