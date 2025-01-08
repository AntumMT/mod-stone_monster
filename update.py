#!/usr/bin/env python3

# Script to fetch changes from upstream mobs_monster mod.

import codecs
import errno
import os
import re
import shutil
import sys

from urllib.error import HTTPError

try:
	import wget
except ModuleNotFoundError:
	sys.stderr.write("\nERROR: module 'wget' required for fetching remote resources\n")
	sys.exit(errno.ENOENT)


upstream = "https://codeberg.org/tenplus1/mobs_monster"
ref = "master"
mob_name = "stone_monster"
mob_title = "Stone Monster"


def getRefUrl(path):
	return "{}/raw/commit/{}/{}".format(upstream, ref, path)


# FIXME: how to fetch directory
def download(url, target=None, exit_on_error=True):
	if target == None:
		target = os.path.basename(url)

	print("fetching resource `{}` from `{}`".format(target, url))

	temp = "__temp__"
	if os.path.isdir(temp):
		shutil.rmtree(temp)
	elif os.path.exists(temp):
		os.remove(temp)

	try:
		wget.download(url, temp)
		# wget doesn't output line ending to stdout
		print()
	except HTTPError:
		if not exit_on_error:
			print("resource does not exist on remote: {}".format(url))
			return errno.ENOENT
		sys.stderr.write("\nERROR: failed to fetch resource: {}\n".format(url))
		sys.exit(errno.ENOENT)

	if target != temp:
		if os.path.isdir(target):
			shutil.rmtree(target)
		elif os.path.exists(target):
			os.remove(target)
		shutil.move(temp, target)

	return 0


def updateNamespace(target):
	if not os.path.isfile(target):
		sys.stderr.write("\nERROR: [{}] file not found, cannot update namespace".format(target))
		sys.exit(errno.ENOENT)

	fin = codecs.open(target, "r", "utf-8")
	content = fin.read().replace("\r\n", "\n").replace("\r", "\n")
	fin.close()

	content = re.sub("\"mobs_monster:", "\":mobs:", content, flags=re.M)

	lines = content.split("\n")
	for idx in reversed(range(len(lines))):
		li = lines[idx]
		if li.startswith("mobs:register_egg(") or li.startswith("mobs:alias_mob(\"mobs:{}\"".format(mob_name)) or li == "-- spawn egg" or li == "-- compatibility with older mobs mod":
			lines.pop(idx)
		elif ".get_translator(\"mobs_monster\")" in li:
			lines[idx] = li.replace("\"mobs_monster\"", "\"mobs_{}\"".format(mob_name))

	add_info = [
		"if core.global_exists(\"asm\") then",
		"	asm.addEgg({",
		"		name = \"{}\",".format(mob_name),
		"		title = S(\"{}\"),".format(mob_title),
		"		inventory_image = \"default_stone.png\",",
		"		spawn = \"mobs:{}\",".format(mob_name),
		"		ingredients = \"default:stone\",",
		"	})",
		"end",
		"core.register_alias(\"mobs:{0}\", \"spawneggs:{0}\")".format(mob_name),
		"",
		"mobs:alias_mob(\"mobs_monster:{0}\", \"mobs:{0}\") -- compatibility".format(mob_name)
	]
	lines = lines + add_info
	content = "\n".join(lines)
	if not content.endswith("\n"):
		content = content + "\n"

	fout = codecs.open(target, "w", "utf-8")
	fout.write(content)
	fout.close()


def updateLua():
	target = "init.lua"
	download(getRefUrl("{}.lua".format(mob_name)), target)
	updateNamespace(target)


def updateLocale():
	print("updating localization template ...")

	if not os.path.exists("locale"):
		os.makedirs("locale")

	source = "init.lua"
	template = "locale/template.txt"

	fin = codecs.open(source, "r", "utf-8")
	content = fin.read()
	fin.close()

	strings_found = []

	p = re.compile(r"S\(\".*\"\)")
	m = p.search(content)
	while m:
		s = m.group(0)[3:-2]
		strings_found.append(s)
		content = content[m.end():]
		m = p.search(content)

	if len(strings_found) > 0:
		t_out = "# textdomain:mobs_{}\n\n".format(mob_name)
		for f in strings_found:
			t_out = t_out + f + "=\n"

		fout = codecs.open(template, "w", "utf-8")
		fout.write(t_out)
		fout.close()


def updateConf():
	download(getRefUrl("mod.conf"))

	fin = codecs.open("mod.conf", "r", "utf-8")
	content = fin.read().replace("\r\n", "\n").replace("\r", "\n")
	fin.close()

	lines = content.split("\n")

	for idx in range(len(lines)):
		li = lines[idx]
		if li.startswith("name ="):
			lines[idx] = "name = {}".format(mob_name)
		elif li.startswith("optional_depends ="):
			if "asm_spawneggs" not in li.replace(" ", "").split("=")[1].split(","):
				lines[idx] = lines[idx] + ", asm_spawneggs"

	fout = codecs.open("mod.conf", "w", "utf-8")
	fout.write("\n".join(lines))
	fout.close()


def updateTextures():
	file_basename = "mobs_{}".format(mob_name)
	if not os.path.exists("textures"):
		os.mkdir("textures")
	file_path = "textures/{}.png".format(file_basename)
	download(getRefUrl(file_path), file_path)
	for idx in range(2, 50):
		file_path = "textures/{}{}.png".format(file_basename, idx)
		if download(getRefUrl(file_path), file_path, False) != 0:
			break


if __name__ == "__main__":
	# change to source root
	os.chdir(os.path.dirname(__file__))

	script = os.path.basename(__file__)

	args = sys.argv[1:]

	if "-h" in args or "--help" in args:
		print("Usage: {} [--ref=<refname>]".format(script))
		print()
		print("    --ref: Use reference `refname` instead of \"master\".")
		sys.exit(0)

	for arg in args:
		if arg.startswith("--ref="):
			ref = arg[6:]
			break

	updateLua()
	updateLocale()
	updateConf()

	# license
	download(getRefUrl("license.txt"))

	# models
	if not os.path.exists("models"):
		os.mkdir("models")
	download(getRefUrl("models/mobs_{}.b3d".format(mob_name)), "models/mobs_{}.b3d".format(mob_name))

	# sounds
	if not os.path.exists("sounds"):
		os.mkdir("sounds")
	download(getRefUrl("sounds/mobs_{}.ogg".format(mob_name.replace("_", ""))), "sounds/mobs_{}.ogg".format(mob_name.replace("_", "")))

	# textures
	updateTextures()
