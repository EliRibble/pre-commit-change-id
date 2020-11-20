"All module logic."
import argparse
import logging
import os
import re
import sys
import uuid
from typing import Dict, Tuple

import precommit_message_preservation

LOGGER = logging.getLogger("precommit-changeid")


def create_change_id() -> str:
	"Create a Change-Id that Gerrit will accept."
	return "I" + uuid.uuid4().hex + uuid.uuid4().hex[:8]

def get_suggested_content(filename: str) -> str:
	"""Get the full content suggested for the git commit message.

	Suggested content should look like:

	[message provided on commandline]
	[previously saved message, if any]
	[injected tags]
	[verbose code added by 'git commit -v']

	Args:
		The file path to the existing commit message provided by 'git commit -m'.
	Returns:
		The suggested content.
	"""
	try:
		with open(filename, "r") as inp:
			current_message = inp.read()
	except OSError:
		current_message = ""

	current_message, verbose_code = split_verbose_code(current_message)
	# Remove any trailing whitespace so we don't have blank lines between our tags.
	current_message = current_message.rstrip()
	previous_commit_message = precommit_message_preservation.get_cached_message()
	if previous_commit_message and current_message:
		current_message, change_id = extract_change_id(current_message)
		previous_commit_message, previous_change_id = extract_change_id(previous_commit_message)
		change_id = change_id or previous_change_id
		suggested = (current_message +
			"\n# ==== previously saved message below ====\n" +
			previous_commit_message)
	else:
		suggested = current_message or previous_commit_message
		suggested, change_id = extract_change_id(suggested)

	change_id = change_id or create_change_id()
	# Parse out the current tags and organize them appropriately
	suggested = suggested.rstrip() + "\n\nChange-Id: " + change_id
	if verbose_code:
		suggested += verbose_code
	return suggested

def extract_change_id(content: str) -> Tuple[str, str]:
	"""Extract the Change-Id tag from a commit message, if any.

	Returns:
		The content without the Change-Id tag, if present, otherwise the full
		content and an empty string.
	"""
	lines = []
	change_id = ""
	for line in content.split("\n"):
		match = re.match(r"^Change-Id:\s*(I[0-9a-f]{8,40})", line, re.IGNORECASE)
		if not match:
			lines.append(line)
			continue
		new_line = line[:match.start()] + line[match.end():]
		lines.append(new_line)
		change_id = match.group(1)
	return "\n".join(lines), change_id

def has_editor() -> bool:
	"Return whether or not git will be using an editor for the commit message."
	return os.environ.get("GIT_EDITOR") != ":"

def main() -> None:
	"Main entrypoint for the hook."
	parser = argparse.ArgumentParser()
	parser.add_argument("file", help="The current git commit message file, provided by pre-commit.")
	parser.add_argument("-v", "--verbose", action="store_true", help="Use verbose logging.")
	args = parser.parse_args()

	logging.basicConfig(
		level = logging.DEBUG if args.verbose else logging.INFO
	)

	if not has_editor():
		sys.exit(0)

	suggested_content = get_suggested_content(args.file)

	with open(args.file, "w") as out:
		out.write(suggested_content)
		LOGGER.debug("Write new commit message to %s", args.file)

def split_verbose_code(current_message: str) -> Tuple[str, str]:
	"""Split code message on the 'git commit -v' verbose marker.

	This uses a less stable marker than the official marker. The stable marker
	is ------------ >8 -----------. However, we want to ensure we don't
	interleave the tag suggestions into the comments in front of this marker,
	so we use the less-stable English explanatory comment.

	Args:
		current_message: The current commit message to split.
	Returns:
		The commit message before the '-v' comment section and the comments
		and code after the '-v' comment section, as a tuple of text.
	"""
	index = current_message.find("\n# Please enter the commit message for your changes.")
	if index == -1:
		return (current_message, "")
	return current_message[:index], current_message[index:]
