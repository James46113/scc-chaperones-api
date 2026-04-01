#!/usr/bin/env python3

import sys
import re
import os
import math

# Regex to match ANSI escape sequences
ansi_escape = re.compile(r'\033\[[0-9;]*m')
page_size = (os.get_terminal_size().lines - 6) // 2
start = 0
search = ""
help = False
filterArgs = ["", "", "", "", "", 0]
filterArgsNegation = [False for _ in range(6)]
duration_greater_than = False
logs = []
lines_printed = 0
page_size_override = 0

TIMESTAMP = 0
USER = 1
METHOD = 2
PATH = 3
STATUS = 4
DURATION = 5


def println(line=""):
	global lines_printed
	lines_printed += 1
	print(line)

def ansi_ljust(text: str, width: int, fillchar: str = " ") -> str:
    # Strip ANSI codes to calculate visible length
    stripped_text = ansi_escape.sub("", text)
    padding = max(0, width - len(stripped_text))
    return text + (fillchar * padding)

def strip_ansi(text: str) -> str:
	# Strip ANSI codes from the text
	return ansi_escape.sub("", text)

def show_filters():
	if num_shown_filters() != 0:
		println()

	if search != "":
		println(f"Search: {search}")

	if filterArgs[TIMESTAMP] != "":
		println(f"Timestamp: {filterArgs[TIMESTAMP]}{'!' if filterArgsNegation[TIMESTAMP] else ''}")

	if filterArgs[USER] != "":
		println(f"User: {filterArgs[USER]}{'!' if filterArgsNegation[USER] else ''}")

	if filterArgs[METHOD] != "":
		println(f"Method: {filterArgs[METHOD]}{'!' if filterArgsNegation[METHOD] else ''}")

	if filterArgs[PATH] != "":
		println(f"Path: {filterArgs[PATH]}{'!' if filterArgsNegation[PATH] else ''}")

	if filterArgs[STATUS] != "":
		println(f"Status: {filterArgs[STATUS]}{'!' if filterArgsNegation[STATUS] else ''}")

	if filterArgs[DURATION] > 0:
		if duration_greater_than:
			println(f"Duration: >{filterArgs[DURATION]}ms{'!' if filterArgsNegation[DURATION] else ''}")
		else:
			println(f"Duration: <{filterArgs[DURATION]}ms{'!' if filterArgsNegation[DURATION] else ''}")

	println("\033[0m")


def num_shown_filters():
	num = 0.0
	if search != "":
		num += 1
	if filterArgs[TIMESTAMP] != "":
		num += 1
	if filterArgs[USER] != "":
		num += 1
	if filterArgs[METHOD] != "":
		num += 1
	if filterArgs[PATH] != "":
		num += 1
	if filterArgs[DURATION] != 0:
		num += 1
	if filterArgs[STATUS] != "":
		num += 1
	if num > 0:
		num += 1
	return num

def get_page_size(help):
	page_size = 0
	if page_size_override > 0:
		page_size = page_size_override
	else:
		page_size = os.get_terminal_size().lines - 6
	if help:
		page_size = page_size - 13

	return page_size
	

def print_logs():
	global start, help, page_size, lines_printed, help
	lines_printed = 0
	page_size = get_page_size(help) // 2

	page_size -= math.ceil(num_shown_filters() / 2)
	
	filtered_logs = filter_logs()

	no_logs = False
	if len(filtered_logs) == 0:
		no_logs = True
		filtered_logs = [["", "", "", "\033[3;90mNo Results\033[0m", "", ""]]

	logs_to_display = filtered_logs[start:start+page_size]
	max_lengths = [len(max(value, key=len)) for value in [[strip_ansi(log[i]) for log in logs_to_display] for i in range(len(logs_to_display[0]))]]
	max_lengths = [max(length, len(header)) for length, header in zip(max_lengths, ["Timestamp", "User", "Method", "Path", "Status", "Response Time"])]

	println("\033[2J╔═" + "═╦═".join(["═"*length for length in max_lengths]) + "═╗")
	println("║ " + " ║ ".join([ansi_ljust(header, max_lengths[ind]) for ind, header in enumerate(["\033[1mTimestamp", "User", "Method", "Path", "Status", "Duration\033[0m"])]) + " ║")	
	println("╠═" + "═╬═".join(["═"*length for length in max_lengths]) + "═╣")


	for log in logs_to_display:
		println("║ " + " ║ ".join([ansi_ljust(value, max_lengths[ind]) for ind, value in enumerate(log)]) + " ║")
		if log != logs_to_display[-1]:
			println("╟─" + "─╫─".join(["─"*length for length in max_lengths]) + "─╢") 

	println("╚═" + "═╩═".join(["═"*length for length in max_lengths]) + "═╝")

	upper_bound = 0 if no_logs else start + len(logs_to_display)

	println(f"\033[3mShowing {start} to {upper_bound} of {len(filtered_logs)-1} logs")

	show_filters()

	if help:
		if page_size_override == 0:
			print("\n"*(os.get_terminal_size().lines - lines_printed - 13), end="")


		help_details = [
			["\033[1mCommand","", "Args", "Description\033[0m"],
			["quit", "(q)", "", "Quit the logs viewer"],
			["reload", "(r)", "", "Reload the logs"],
			["next", "(n)", "<number>", "Next (back in time), default is 20"],
			["back", "(b)", "<number>", "Back (forwards in time), default is 20"],
			["goto", "(g)", "<number>", "Go to log number. Must be between 0 and the number of logs"],
			["search", "(s)", "<string>", "Search by string. 'clear' or no arg to remove filter"],
			["filter", "(f)", "-[t, u, m, p, s, d] <value>[!]", "Filter by args. '!' negates. 'clear' or no value to remove filter."],
			["pagesize", "(p)", "<number>", "Number of logs per page. Detection does not work on all terminals"],
			["help", "(h)", "", "Display this help menu"],

		]
		help_max_lengths = [len(max(value, key=len)) for value in [[strip_ansi(log[i]) for log in help_details] for i in range(len(help_details[0]))]]
		help_max_lengths[-1] = 0
		for command in help_details:
			println("".join(ansi_ljust(string, help_max_lengths[ind]+5) for ind, string in enumerate(command)))
		println()
		println("Press arrow keys (then enter) for next/previous logs")
		help = False
	else:
		if page_size_override == 0:
			print("\n"*(os.get_terminal_size().lines - lines_printed - 1), end="")


def move_to_newer(amount):
	global start
	if start-amount >= 0:
		start -= amount

def move_to_previous(amount):
	global start

	if start+amount < len(filter_logs()):
		start += amount


def show_help():
	global help
	help = True

def filter_logs():
	global search, logs, duration_greater_than, filterArgs

	filtered_logs = [log for log in logs if search in "".join(log)]

	for ind, arg in enumerate(filterArgs):
		if arg != "" and not ind in [DURATION, STATUS]:
			filtered_logs = [log for log in filtered_logs if (arg in log[ind]) != filterArgsNegation[ind]]

	if filterArgs[DURATION] > 0:
		if duration_greater_than:
			filtered_logs = [log for log in filtered_logs if (int(strip_ansi(log[DURATION])[:-2]) > filterArgs[DURATION]) != filterArgsNegation[DURATION]]
		else:
			filtered_logs = [log for log in filtered_logs if (int(strip_ansi(log[DURATION])[:-2]) < filterArgs[DURATION]) != filterArgsNegation[DURATION]]
	
	if filterArgs[STATUS] != "":
		if filterArgs[STATUS].endswith("xx"):
			filtered_logs = [log for log in filtered_logs if (strip_ansi(log[STATUS]).startswith(filterArgs[STATUS][:-2])) != filterArgsNegation[STATUS]]
		elif filterArgs[STATUS].endswith("x"):
			filtered_logs = [log for log in filtered_logs if (strip_ansi(log[STATUS]).startswith(filterArgs[STATUS][:-1])) != filterArgsNegation[STATUS]]
		else:
			filtered_logs = [log for log in filtered_logs if (strip_ansi(log[STATUS]).startswith(filterArgs[STATUS])) != filterArgsNegation[STATUS]]
	
	return filtered_logs

def reload_logs():
	global logs
	with open("/logs/app.log", "r") as f:	
		lines = [line.strip() for line in f.readlines()]
		lines.reverse()
		
		if len(sys.argv) > 1:
			search = sys.argv[1]
			lines = [line for line in lines if search in line]

		logs = [line.split(",") for line in lines]
		logs_to_remove = []

		for log in logs:
			try:
				# colour status code
				if log[STATUS].startswith("2"):
					log[STATUS] = "\033[92m" + log[STATUS] + "\033[0m"
				elif log[STATUS].startswith("4"):
					log[STATUS] = "\033[93m" + log[STATUS] + "\033[0m"
				elif log[STATUS].startswith("5"):
					log[STATUS] = "\033[91;5;52m" + log[STATUS] + "\033[0m"

				# colour response time
				response_time = int(log[DURATION][:-2])
				if response_time > 200:
					log[DURATION] = "\033[91m" + log[DURATION] + "\033[0m"
				elif response_time > 100:
					log[DURATION] = "\033[93m" + log[DURATION] + "\033[0m"
				else:
					log[DURATION] = "\033[92m" + log[DURATION] + "\033[0m"

				# colour method
				if log[METHOD] == "GET":
					log[METHOD] = "\033[92m" + log[METHOD] + "\033[0m"
				elif log[METHOD] == "POST":
					log[METHOD] = "\033[93m" + log[METHOD] + "\033[0m"
				elif log[METHOD] == "PUT":
					log[METHOD] = "\033[95m" + log[METHOD] + "\033[0m"
				elif log[METHOD] == "DELETE":
					log[METHOD] = "\033[91m" + log[METHOD] + "\033[0m"
				elif log[METHOD] == "PATCH":
					log[METHOD] = "\033[94m" + log[METHOD] + "\033[0m"
			except IndexError:
				logs_to_remove.append(log)
		for log in logs_to_remove:
			logs.remove(log)
		print(f"Removed {len(logs_to_remove)} faulty logs")


def set_args(arg, value):
	global filterArgs
	if value == "clear" or value.startswith("-"):
		filterArgs[arg] = ""
	else:
		if arg == DURATION:
			try:
				if value[-1] == "!":
					try:
						filterArgs[arg] = int(value[:-1])
						filterArgsNegation[arg] = True
					except ValueError:
						show_help()
					return
				
			except IndexError:
				pass
			try:
				filterArgs[arg] = int(value)
				filterArgsNegation[arg] = False
			except ValueError:
				show_help()
		else:
			try:
				if value[-1] == "!":
					filterArgsNegation[arg] = True
					filterArgs[arg] = value[:-1]
					return;
			except IndexError:
				pass

			filterArgs[arg] = value
			filterArgsNegation[arg] = False

reload_logs()
while True:
	try:
		print_logs()

		cmd = input(": ").split(" ")

		if cmd[0] == "q" or cmd[0] == "quit":
			break
		elif cmd[0] in {"n", "\x1b[B", "", "next"}:
			if len(cmd) > 1:
				try:
					move_to_previous(int(cmd[1]))
				except ValueError:
					show_help()
			else:
				move_to_previous(page_size)

		elif cmd[0] in {"b", "\x1b[A", "back"}:
			if len(cmd) > 1:
				try:
					move_to_newer(int(cmd[1]))
				except ValueError:
					show_help()
			else:
				move_to_newer(page_size)
		
		elif cmd[0] in ["s", "search"]:
			try:
				if cmd[1] == "clear":
					search = ""
				else:
					search = cmd[1]
			except:
				search = ""
			start = 0

		elif cmd[0] in ["f", "filter"]:
			try:
				if cmd[1] == "clear":
					filterArgs = ["", "", "", "", "", 0]
					start = 0
					continue
				
				try:
					timestamp_flag = cmd.index("-t")
					set_args(TIMESTAMP, cmd[timestamp_flag + 1])
				except IndexError:
					set_args(TIMESTAMP, "")
				except ValueError:
					pass

				try:
					user_flag = cmd.index("-u")
					set_args(USER, cmd[user_flag + 1])
				except IndexError:
					set_args(USER, "")
				except ValueError:
					pass

				try:
					method_flag = cmd.index("-m")
					set_args(METHOD, cmd[method_flag + 1])
				except IndexError:
					set_args(METHOD, "")
				except ValueError:
					pass

				try:
					url_flag = cmd.index("-p")
					set_args(PATH, cmd[url_flag + 1])
				except IndexError:
					set_args(PATH, "")
				except ValueError:
					pass

				try:
					status_flag = cmd.index("-s")
					set_args(STATUS, cmd[status_flag + 1])
				except IndexError :
					set_args(STATUS, "")
				except ValueError:
					pass

				try:
					duration_flag = cmd.index("-d")
					if cmd[duration_flag + 1][0] == ">":
						duration_greater_than = True
					elif cmd[duration_flag + 1][0] == "<":
						duration_greater_than = False
					else:
						raise ValueError("Invalid operator")
					set_args(DURATION, cmd[duration_flag + 1][1:])
				except IndexError:
					set_args(DURATION, "0")
				except ValueError:
					pass

			except Exception as e:
				print(e)
				filterArgs = ["", "", "", "", "", 0]
			start = 0

		elif cmd[0] in ["g", "goto"]:
			try:
				if not (int(cmd[1]) > len(logs) or int(cmd[1]) < 0):
					start = int(cmd[1])
				else:
					show_help()
			except:
				show_help()

		elif cmd[0] in ["r", "reload"]:
			reload_logs()
			start = 0

		elif cmd[0] in ["p", "pagesize"]:
			try:
				page_size_override = int(cmd[1]) * 2
			except:
				page_size_override = 0

		elif cmd[0] in ["h", "help"]:
			show_help()

		else:
			show_help()

	except KeyboardInterrupt:
		print()
		break
