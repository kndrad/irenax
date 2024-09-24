import re
from bs4 import BeautifulSoup
from bs4.element import SoupStrainer
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta


def is_work(title):
	# pattern = r"^[A-Za-z]+\d+\*?$"
	# is_work = bool(re.match(pattern, title)) and title != "DW5"
	is_work = True

	if title in ("DWS", "DW5", "DWŚ", "T", "KREW", "N", "C", "C5", "W"):
		is_work = False

	return is_work

def is_training(title):
	return title == 'VS'


def calculate_night_hours(start, end):
	if start.tzinfo is None:
		start = start.replace(tzinfo=tz.tzutc()).astimezone(local_tz)
	if end.tzinfo is None:
		end = end.replace(tzinfo=tz.tzutc()).astimezone(local_tz)

	night_start = start.replace(hour=22, minute=0, second=0, microsecond=0)
	night_end = (start + timedelta(days=1)).replace(
		hour=5, minute=0, second=0, microsecond=0
	)

	if end < night_start or start > night_end:
		return 0

	overlap_start = max(start, night_start)
	overlap_end = min(end, night_end)

	if overlap_end < overlap_start:
		overlap_end += timedelta(days=1)

	night_duration = overlap_end - overlap_start
	return night_duration.total_seconds() / 3600  # Convert to hours


@dataclass
class _action:
	train: str
	name: str
	start_location: str
	start_time: str
	end_location: str
	end_time: str

	def __str__(self):
		return f"{self.train} {self.name}, {self.start_location} {self.start_time}->{self.end_location} {self.end_time}".strip().replace(
			"\n", "|||"
		)


class Duty:
	def __init__(self, id: str, title: str, actions: List[_action]):
		self.id = id
		self.title = title
		self.actions = actions

	def __repr__(self):
		return f"Duty({self.title}, {self.id}, {len(self.actions)} actions)"

	def __iter__(self):
		return iter(self.actions)

	def event_description(self):
		description = "\n".join(str(action) for action in self.actions)
		return description


_rows_re = re.compile("^(duty-components).*")
_urlid_re = re.compile(r"(id=)(?P<id>\d+)")

_undefined = "UNDEFINED"
_DATE_FORMAT = "%Y-%m-%d"

def get_duty(session, title, date) -> Duty:
	if is_training(title):
		return Duty(_undefined, title, [])

	date_only = date.strftime(_DATE_FORMAT)
	url = (
		f"https://irena1.intercity.pl/mbweb/main/ivu/desktop/"
		f"_-any-duty-table?division=&depot=&abbreviation={title}&date={date_only}&"
	)

	print(f"Requesting duty {title} {date_only}")
	response = session.get(url)
	response.raise_for_status()

	strainer = SoupStrainer(name="div", class_="allocation-container display-full")
	soup = BeautifulSoup(
		markup=response.content, features="html.parser", parse_only=strainer
	)

	try:
		node = soup.find(name="div", class_="clickable")
		url_id = _urlid_re.search(node["data-url"])["id"]
	except AttributeError:
		raise Exception("failed to find duty id within container")

	url = f"https://irena1.intercity.pl/mbweb/main/ivu/desktop/any-duty-details?id={url_id}&beginDate={date}&"
	response = session.get(url)
	response.raise_for_status()

	strainer = SoupStrainer(name="tbody")
	soup = BeautifulSoup(
		markup=response.content, features="html.parser", parse_only=strainer
	)

	keys = [
		("train", "trip_numbers mdl-data-table__cell--non-numeric"),
		("name", "type_long_name mdl-data-table__cell--non-numeric"),
		(
			"start_location",
			"start_location_long_name mdl-data-table__cell--non-numeric",
		),
		("start_time", "start_time mdl-data-table__cell--non-numeric"),
		("end_location", "end_location_long_name mdl-data-table__cell--non-numeric"),
		("end_time", "end_time mdl-data-table__cell--non-numeric"),
	]

	actions = []
	for row in soup.find_all(name="tr", attrs={"class": _rows_re}):
		data = {}
		for name, value in keys:
			cell = row.find("td", class_=value)
			if cell:
				data[name] = cell.find("span", class_="value").text.strip()
			else:
				data[name] = ""
		actions.append(_action(**data))

	return Duty(url_id, title, actions)
