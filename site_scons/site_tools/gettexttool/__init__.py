""" This tool allows generation of gettext .mo compiled files, pot files from source code files
and pot files for merging.

Three new builders are added into the constructed environment:

- gettextMoFile: generates .mo file from .pot file using msgfmt.
- gettextPotFile: Generates .pot file from source code files.
- gettextMergePotFile: Creates a .pot file appropriate for merging into existing .po files.

To properly configure get text, define the following variables:

- gettext_package_bugs_address
- gettext_package_name
- gettext_package_version


"""
from SCons.Action import Action
import os
import shutil
import struct


def exists(env):
	return True


def py_msgfmt(target, source, env):
	src_file = str(source[0])
	dst_file = str(target[0])
	MESSAGES = {}
	with open(src_file, 'r', encoding='utf-8', errors='replace') as f:
		lines = f.readlines()

	msgid = None
	msgstr = None
	in_msgid = False
	in_msgstr = False

	for line in lines:
		line = line.strip()
		if not line or line.startswith('#'):
			continue
		if line.startswith('msgid '):
			if msgid is not None and msgstr is not None:
				MESSAGES[msgid] = msgstr
			try:
				msgid = eval(line[6:])
			except Exception:
				msgid = line[6:].strip('"')
			msgstr = None
			in_msgid = True
			in_msgstr = False
		elif line.startswith('msgstr '):
			try:
				msgstr = eval(line[7:])
			except Exception:
				msgstr = line[7:].strip('"')
			in_msgid = False
			in_msgstr = True
		elif line.startswith('"') and line.endswith('"'):
			try:
				val = eval(line)
			except Exception:
				val = line.strip('"')
			if in_msgid and msgid is not None:
				msgid += val
			elif in_msgstr and msgstr is not None:
				msgstr += val
	if msgid is not None and msgstr is not None:
		MESSAGES[msgid] = msgstr

	keys = sorted(MESSAGES.keys())
	offsets = []
	ids = b''
	strs = b''
	for key in keys:
		val = MESSAGES[key]
		key_b = key.encode('utf-8')
		val_b = val.encode('utf-8')
		offsets.append((len(ids), len(key_b), len(strs), len(val_b)))
		ids += key_b + b'\0'
		strs += val_b + b'\0'

	key_start = 7 * 4 + len(keys) * 8 * 2
	val_start = key_start + len(ids)

	k_offsets = []
	v_offsets = []
	for k_off, k_len, v_off, v_len in offsets:
		k_offsets.extend([k_len, key_start + k_off])
		v_offsets.extend([v_len, val_start + v_off])

	output = struct.pack(
		'Iiiiiii',
		0x950412de,
		0,
		len(keys),
		7 * 4,
		7 * 4 + len(keys) * 8,
		0,
		0
	)
	output += struct.pack(f'{len(k_offsets)}i', *k_offsets)
	output += struct.pack(f'{len(v_offsets)}i', *v_offsets)
	output += ids
	output += strs

	os.makedirs(os.path.dirname(dst_file), exist_ok=True)
	with open(dst_file, 'wb') as f:
		f.write(output)
	return 0


XGETTEXT_COMMON_ARGS = (
	"--msgid-bugs-address='$gettext_package_bugs_address' "
	"--package-name='$gettext_package_name' "
	"--package-version='$gettext_package_version' "
	"--keyword=pgettext:1c,2 "
	"-c -o $TARGET $SOURCES"
)


def generate(env):
	env.SetDefault(gettext_package_bugs_address="example@example.com")
	env.SetDefault(gettext_package_name="")
	env.SetDefault(gettext_package_version="")

	if shutil.which("msgfmt"):
		mo_action = Action("msgfmt -o $TARGET $SOURCE", "Compiling translation $SOURCE")
	else:
		mo_action = Action(py_msgfmt, "Compiling translation $SOURCE")

	env['BUILDERS']['gettextMoFile'] = env.Builder(
		action=mo_action,
		suffix=".mo",
		src_suffix=".po"
	)

	env['BUILDERS']['gettextPotFile'] = env.Builder(
		action=Action("xgettext " + XGETTEXT_COMMON_ARGS, "Generating pot file $TARGET"),
		suffix=".pot")

	env['BUILDERS']['gettextMergePotFile'] = env.Builder(
		action=Action(
			"xgettext " + "--omit-header --no-location " + XGETTEXT_COMMON_ARGS,
			"Generating pot file $TARGET"
		),
		suffix=".pot"
	)
