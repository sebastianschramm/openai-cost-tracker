import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import click
from opentelemetry import trace
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from cost_tracker.openai_token_prices import token_prices_per_model


def init_span(span):
    return {
        "span_name": span.name,
        "start_time": (
            span.start_time.isoformat()
            if isinstance(span.start_time, datetime)
            else span.start_time
        ),
        "end_time": (
            span.end_time.isoformat()
            if isinstance(span.end_time, datetime)
            else span.end_time
        ),
        "llm_request_type": "",
        "gen_ai_request_model": "",
        "gen_ai_response_model": "",
        "llm_usage_total_tokens": 0,
        "gen_ai_usage_prompt_tokens": 0,
        "gen_ai_usage_completion_tokens": 0,
        "attributes": {},
    }


def populate_span_data(span_data):
    span_data["llm_request_type"] = span_data["attributes"].get("llm.request.type", "")
    span_data["gen_ai_request_model"] = span_data["attributes"].get(
        "gen_ai.request.model", ""
    )
    span_data["gen_ai_response_model"] = span_data["attributes"].get(
        "gen_ai.response.model", ""
    )
    span_data["llm_usage_total_tokens"] = span_data["attributes"].get(
        "llm.usage.total_tokens", 0
    )
    span_data["gen_ai_usage_prompt_tokens"] = span_data["attributes"].get(
        "gen_ai.usage.prompt_tokens", 0
    )
    span_data["gen_ai_usage_completion_tokens"] = span_data["attributes"].get(
        "gen_ai.usage.completion_tokens", 0
    )
    return span_data


class CustomFileSpanExporter(ConsoleSpanExporter):

    def __init__(self, log_content: bool = False):
        """
        Custom span exporter that logs the span data to a file.

        Args:
            log_content (bool, optional): Whether to log prompts and response content.
            Note: Prompts/content might contain sensitive data. Defaults to False.
        """
        super().__init__()

        self.log_content = log_content

        self.logger = logging.getLogger("token_logger")
        self.logger.setLevel(logging.INFO)
        self.init_time = datetime.now().isoformat()

        self._init_file_handler()

    def _init_file_handler(self):
        file_handler = logging.FileHandler(f"traces_{self.init_time}.log")
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def export(self, spans):
        for span in spans:
            span_data = init_span(span)
            span_data["init_time"] = self.init_time

            for key, value in span.attributes.items():
                if self.log_content or "content" not in key:
                    span_data["attributes"][key] = value
            if span_data["attributes"]:
                span_data = populate_span_data(span_data)

            self.logger.info(json.dumps(span_data))

        return super().export(spans)


def get_exporter(log_openai_content: bool):
    return CustomFileSpanExporter(log_openai_content)


def get_provider(exporter):
    provider = TracerProvider(
        resource=Resource.create({"service.name": "openai-cost-tracker"})
    )
    span_processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(span_processor)
    return provider


def init_tracker(log_openai_content: bool = True):
    """Import and run this in front of any method that you want to trace"""
    exporter = get_exporter(log_openai_content)
    provider = get_provider(exporter)
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument(
        provider=provider, log_payload=True, max_payload_length=100_000
    )


def get_usage_data(file: Path):
    with open(file) as f:
        rows = [json.loads(row) for row in f.readlines()]
    return rows


def get_token_usage_and_costs_from_file(
    file: Path,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    results = get_usage_data(file)

    usage_and_costs = {}
    for result in results:
        init_time = result["init_time"]
        model = result["gen_ai_response_model"]
        prompt_tokens = result["gen_ai_usage_prompt_tokens"]
        completion_tokens = result["gen_ai_usage_completion_tokens"]

        if init_time not in usage_and_costs:
            usage_and_costs[init_time] = {"models": {}, "total_cost_usd": 0}

        if model not in usage_and_costs[init_time]["models"]:
            usage_and_costs[init_time]["models"][model] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": 0,
            }

        if model in token_prices_per_model:
            prompt_cost = prompt_tokens * token_prices_per_model[model]["prompt"]
            completion_cost = (
                completion_tokens * token_prices_per_model[model]["completion"]
            )
            total_cost = prompt_cost + completion_cost
            usage_and_costs[init_time]["models"][model]["cost_usd"] = round(
                total_cost, 2
            )
            usage_and_costs[init_time]["total_cost_usd"] += total_cost
        else:
            usage_and_costs[init_time]["models"][model]["cost_usd"] = None

    for init_time in usage_and_costs:
        usage_and_costs[init_time]["total_cost_usd"] = round(
            usage_and_costs[init_time]["total_cost_usd"], 2
        )

    return usage_and_costs


@click.command()
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    required=True,
    help="File with logged OpenAI requests.",
)
def display_costs(file):
    usage_and_costs = get_token_usage_and_costs_from_file(file)
    click.echo(click.style("OpenAI costs:", bold=True, italic=True, fg="red"))
    for k, v in usage_and_costs.items():
        click.echo(click.style(f"{k} -> {v}", bold=True, fg="red"))


if __name__ == "__main__":
    display_costs()
