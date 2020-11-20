"Tests for the eureka_prepare_commit_message module"
import contextlib
import re
from typing import Generator
import unittest
import unittest.mock

from nose2.tools import params # type: ignore

import precommit_changeid as pci

SAMPLE_VERBOSE_COMMIT_LINES = [
		"This is some summary line.",
		"",
		"You'll notice that even though this is just a test I have ",
		"a properly formatted fake git commit message here. That's ",
		"dedication to my craft, baby.",
		"# Please enter the commit message for your changes. Lines starting",
		"# with '#' will be ignored, and an empty message aborts the commit.",
		"#",
		"# On branch master",
		"# Your branch is up to date with 'eureka/master'.",
		"#",
		"# Changes to be committed:",
		"#   modified:   .pre-commit-config.yaml",
		"#",
		"# ------------------------ >8 ------------------------",
		"# Do not modify or remove the line above.",
		"# Everything below it will be ignored.",
		"diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml",
		"index d4fa34892..ae20e5c0a 100644",
		"--- a/.pre-commit-config.yaml",
		"+++ b/.pre-commit-config.yaml",
		"@@ -31,13 +31,13 @@ repos:",
		"...and so on.",
	]
SAMPLE_VERBOSE_COMMIT = "\n".join(SAMPLE_VERBOSE_COMMIT_LINES)
SAMPLE_VERBOSE_COMMIT_CONTENT = "\n".join(SAMPLE_VERBOSE_COMMIT_LINES[:5])
SAMPLE_VERBOSE_COMMIT_DIFF = "\n" + "\n".join(SAMPLE_VERBOSE_COMMIT_LINES[5:])

@contextlib.contextmanager
def fake_cached_message(message: str) -> Generator[None, None, None]:
	"Patch the routine to get the cached message to return something."
	with unittest.mock.patch(
		"precommit_message_preservation.get_cached_message",
		return_value=message):
		yield


@contextlib.contextmanager
def fake_current_message(message: str) -> Generator[None, None, None]:
	"Patch the routine to get the current message to return something."
	with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=message)):
		yield


@contextlib.contextmanager
def specific_change_id(change_id: str) -> Generator[None, None, None]:
	"Make sure that a specific commit Id tag is generated."
	with unittest.mock.patch("precommit_changeid.create_change_id", return_value=change_id):
		yield


class ChangeIdTestBase(unittest.TestCase):
	"Base class includes some asserts for Change-Id tags."
	def assert_has_changeid(self, content: str, value: str) -> None:
		"Assert that we can find the provided tag in the content."
		_, change_id = pci.extract_change_id(content)
		self.assertEqual(change_id, value)

	def assert_not_has_changeid(self, content: str) -> None:
		"Assert that we can find the provided tag in the content."
		_, change_id = pci.extract_change_id(content)
		self.assertEqual(change_id, "")


class TestGetSuggestedContent(ChangeIdTestBase):
	"Tests for all suggested commit message content."
	def test_previous_commit_message(self) -> None:
		"Test that we use the previous commit message."
		with fake_cached_message("Some summary"):
			suggestion = pci.get_suggested_content("somefile")
			self.assertTrue(suggestion.startswith("Some summary"))

	def test_adds_tag_placeholders(self) -> None:
		"Can we add tag placeholders for all the tags/"
		with fake_cached_message("Some summary"):
			with specific_change_id("Iabcde1234567890"):
				suggestion = pci.get_suggested_content("somefile")
				self.assert_has_changeid(suggestion, "Iabcde1234567890")

	def test_changeid_length(self) -> None:
		"Does our suggested changeid have the proper length?"
		with fake_cached_message(""):
			with fake_current_message("Some summary\n\nmore information"):
				suggestion = pci.get_suggested_content("somefile")
		match = re.search(r"Change-Id: (?P<changeid>\w+)", suggestion)
		assert match
		changeid = match.group("changeid")
		self.assertEqual(len(changeid), 41)

	def test_new_commit_message(self) -> None:
		"Test that we honor what the user provided on the commandline via 'git commit -m"
		with fake_cached_message(""):
			with fake_current_message("Some summary\n\nmore information"):
				suggestion = pci.get_suggested_content("somefile")
			self.assertTrue(suggestion.startswith("Some summary\n\nmore information"))

	def test_new_commit_message_and_previous(self) -> None:
		"Test that we present both the current commit message and previous commit messages."
		with fake_cached_message("An old summary\n\nold details"):
			with fake_current_message("Some summary\n\nmore information"):
				suggestion = pci.get_suggested_content("somefile")
			self.assertTrue(suggestion.startswith("Some summary\n\nmore information"))
			self.assertIn("An old summary\n\nold details", suggestion)
			self.assertIn("previously saved message below", suggestion)

	def test_verbose_commit_no_cached(self) -> None:
		"When user specifies 'git commit -m \"something\" -v' we put everything in the right order."
		with fake_cached_message(""):
			with fake_current_message(SAMPLE_VERBOSE_COMMIT):
				with specific_change_id("Iabcde1234567890"):
					suggestion = pci.get_suggested_content("somefile")
		expected = (SAMPLE_VERBOSE_COMMIT_CONTENT + "\n\n" +
			"Change-Id: Iabcde1234567890" +
			SAMPLE_VERBOSE_COMMIT_DIFF)
		self.assertEqual(suggestion, expected)

	def test_verbose_commit_with_cached(self) -> None:
		"When user specifies 'git commit -m \"something\" -v' we put everything in the right order."
		with fake_cached_message("Some summary.\n\nSome body"):
			with fake_current_message(SAMPLE_VERBOSE_COMMIT):
				with specific_change_id("Iabcde1234567890"):
					suggestion = pci.get_suggested_content("somefile")
		expected = (SAMPLE_VERBOSE_COMMIT_CONTENT + "\n" +
			"# ==== previously saved message below ====\n" +
			"Some summary.\n\n" +
			"Some body\n\n" +
			"Change-Id: Iabcde1234567890" +
			SAMPLE_VERBOSE_COMMIT_DIFF)
		self.assertEqual(suggestion, expected)


	def test_change_id_blank_line_after(self) -> None:
		"Do we detect the Change-Id when present with a blank line after?"
		message = "\n".join((
			"A summary line",
			"",
			"Some detailed message line.",
			"Change-Id: I0102030405060708090001020304050607080900",
			"",
		))
		with fake_current_message(message):
			with fake_cached_message(""):
				suggestion = pci.get_suggested_content("somefile")
		expected = "\n".join((
			"A summary line",
			"",
			"Some detailed message line.",
			"",
			"Change-Id: I0102030405060708090001020304050607080900",
		))
		self.assertEqual(suggestion, expected)

	def test_change_id_blank_line_before(self) -> None:
		"Do we detect the Change-Id when present with a blank line before?"
		message = "\n".join((
			"A summary line",
			"",
			"Some detailed message line.",
			"",
			"Change-Id: I0102030405060708090001020304050607080900",
		))
		with fake_current_message(message):
			with fake_cached_message(""):
				suggestion = pci.get_suggested_content("somefile")
		expected = "\n".join((
			"A summary line",
			"",
			"Some detailed message line.",
			"",
			"Change-Id: I0102030405060708090001020304050607080900",
		))
		self.assertEqual(suggestion, expected)

	def test_change_id_blank_line_both(self) -> None:
		"Do we detect the Change-Id when present with a blank line before?"
		message = "\n".join((
			"A summary line",
			"",
			"Some detailed message line.",
			"",
			"Change-Id: I0102030405060708090001020304050607080900",
		))
		with fake_current_message(message):
			with fake_cached_message(""):
				suggestion = pci.get_suggested_content("somefile")
		expected = "\n".join((
			"A summary line",
			"",
			"Some detailed message line.",
			"",
			"Change-Id: I0102030405060708090001020304050607080900",
		))
		self.assertEqual(suggestion, expected)

class TestExtractTags(ChangeIdTestBase):
	"Tests for logic around extracting tags."

	@params(("Change-Id",), ("CHANGE-ID",), ("change-id",))
	def test_has_change_id_tag(self, name: str) -> None:
		"Test we can detect change_id tags."
		self.assert_has_changeid("Foo\n{}: I12345abcde".format(name), "I12345abcde")

	def test_no_change_id_tag(self) -> None:
		"Test we can detect lack of change_id tag."
		self.assert_not_has_changeid("No\nChange-Id\nTag")

class TestSplitVerboseCode(unittest.TestCase):
	"Test split_verbose_code()"
	def test_no_verbose_code(self) -> None:
		"Ensure we get correct split when no verbose code is present."
		content = "\n".join([
			"This is some summary line.",
			"",
			"This is just some text where I don't have anything useful ",
			"to say. I'm just showing that there's no verbose code here.",
		])
		before, after = pci.split_verbose_code(content)
		self.assertEqual(before, content)
		self.assertEqual("", after)

	def test_verbose_code(self) -> None:
		"Ensure we split between message and verbose code"
		before, after = pci.split_verbose_code("\n".join(SAMPLE_VERBOSE_COMMIT_LINES))
		self.assertEqual(before, SAMPLE_VERBOSE_COMMIT_CONTENT)
		self.assertEqual(after, SAMPLE_VERBOSE_COMMIT_DIFF)
