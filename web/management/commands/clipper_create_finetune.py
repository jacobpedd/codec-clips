import os
import json
import random
from django.core.management.base import BaseCommand
from django.conf import settings
from langsmith import Client
from openai import OpenAI
from web.lib.clipper.generate_clips import TOOLS


class Command(BaseCommand):
    help = "Create a fine-tuning dataset from a LangSmith run"

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str, required=True, help="Name of the run")

        parser.add_argument(
            "--output_file",
            type=str,
            required=False,
            default="./data/dataset.jsonl",
            help="Output .jsonl file to save the dataset to",
        )

    def handle(self, *args, **options):
        run_name = options["name"]
        output_file = options["output_file"]

        if os.path.exists(output_file):
            # Remove the output file if it already exists
            os.remove(output_file)

        with open(output_file, "w") as f:
            f.write("")

        # Initialize LangSmith client
        client = Client(api_key=settings.LANGSMITH_API_KEY)
        oai = OpenAI(api_key=settings.OPENAI_API_KEY)

        runs = client.list_runs(project_name=run_name, is_root=True)
        run_count = 0
        valid_run_count = 0
        for run in runs:
            run_count += 1
            stats = run.feedback_stats
            # # can also access clip_count and iters here
            # # NOTE: Avg is value because n = 1, langsmith is weird
            # if "pass" not in stats or stats["pass"]["avg"] != 1.0:
            #     continue
            if (
                run.outputs is None
                or "output" not in run.outputs
                or "clips" not in run.outputs["output"]
                or len(run.outputs["output"]["clips"]) == 0
            ):
                continue

            # Child calls are where the actual LLM calls happen
            # Reverse the child run IDs to process the most recent runs first
            child_run_ids = run.child_run_ids
            child_run_ids.reverse()
            if child_run_ids is None:
                continue
            child_runs = client.list_runs(id=child_run_ids)

            # Get the most recent llm call that's from the clipper (not metadata generator)
            for child_run in child_runs:
                # Skip non-LLM runs or 4o-mini which does metadata
                # NOTE: Need a better way to skip metadata calls/get just the clip generating calls
                if (
                    child_run.run_type != "llm"
                    or child_run.metadata["ls_model_name"] == "gpt-4o-mini"
                ):
                    continue
                else:
                    messages = child_run.inputs["messages"]

                    # Add the output message
                    output_message = child_run.outputs["generations"][0]["message"]
                    messages.append(output_message)

                    # Convert langsmith messages to openai fine-tuning format
                    messages = [convert_message(message) for message in messages]

                    # Count how many iterations the model took to generate valid clips
                    # - 1 for the system message
                    iterations = (len(messages) - 1) // 2

                    # Only keep all messages if <= 3 iterations x% of the time
                    if iterations > 3 or random.random() > 0.10:
                        # Otherwise, keep only the last (valid) iteration
                        system_message = messages[0]
                        user_message = messages[1]
                        last_message = messages[-1]
                        messages = [system_message, user_message, last_message]

                    data = {
                        "tools": TOOLS,
                        "messages": messages,
                    }

                    moderation = oai.moderations.create(input=json.dumps(data))
                    max_category_score = 0
                    for _, score in moderation.results[0].category_scores:
                        if score > max_category_score:
                            max_category_score = score
                    if max_category_score > 0.6 or moderation.results[0].flagged:
                        print("Flagged")
                        break

                    # Append the messages to the JSONL file
                    with open(output_file, "a") as f:
                        f.write(json.dumps(data) + "\n")
                    valid_run_count += 1
                    break  # Only process the first valid run

        print(f"Processed {run_count} runs, found {valid_run_count} valid runs")


def convert_message(message):
    if message["type"] == "system":
        return {
            "role": "system",
            "content": message["data"]["content"],
        }
    elif message["type"] == "human":
        return {
            "role": "user",
            "content": message["data"]["content"],
        }
    elif message["type"] == "ai":
        if "tool_calls" in message["data"]["additional_kwargs"]:
            return {
                "role": "assistant",
                "tool_calls": message["data"]["additional_kwargs"]["tool_calls"],
            }
        else:
            return {
                "role": "assistant",
                "content": message["data"]["content"],
            }
    elif message["type"] == "chat":
        return {
            "role": "tool",
            "tool_call_id": message["data"]["additional_kwargs"]["tool_call_id"],
            "content": message["data"]["content"],
        }
    else:
        raise ValueError(
            f"Unknown message type: {message['type']}:\n{json.dumps(message, indent=2)}"
        )
