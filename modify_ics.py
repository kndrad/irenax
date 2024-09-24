from icalendar import Calendar, Event, vText, Alarm
import argparse
import yaml
import os
from auth import start_session
import duties
from config import load_config
import yaml
import datetime
import copy


def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def setup_argparse():
    parser = argparse.ArgumentParser(
        description="Adds full description and location to each duty."
    )
    parser.add_argument(
        "--config",
        "-c",
        required=False,
        default=f"{os.environ['HOME']}/.irena.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--input", "-i", help="Path of duties ics file to modify")
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        help="Output of modified duties ics file path (default: same as input)",
    )
    parser.add_argument(
        "--location",
        "-loc",
        default="al. Wojciecha Korfantego 2 Katowice, Polska",
        help="Location in format [Street City, Country]",
    )
    return parser


def main():
    parser = setup_argparse()
    args = parser.parse_args()

    if args.config:
        config = load_config(args.config)
        username = config.get("username") or args.username
        password = config.get("password") or args.password

    if not username or not password:
        parser.error(
            "Username and password are required. Provide them via command line arguments or config file."
        )
        exit(1)

    in_path = args.input
    if not in_path:
        parser.error("Input path of the duties ics file is required")

    if not args.output:
        out_path = "out_" + in_path
    else:
        out_path = args.output
        if out_path == in_path:
            print("Error: out path is the same as in path existing .ics file.")
            exit(1)

    location = args.location
    if not location:
        parser.error("Location for duty events is required")

    try:
        with open(in_path, "rb") as f:  # Open in binary mode
            cal = Calendar.from_ical(f.read())
    except (ValueError, IOError):
        print("Error reading existing calendar. Creating a new one.")
        return

    if cal is None:
        print("Error reading existing calendar.")
        exit(1)

    print("Starting session.")
    session = start_session(username, password)
    print("Authenticated.")

    for event in cal.walk("VEVENT"):
        title = event.get("SUMMARY")

        if title.endswith("*"):
            title = title.replace("*", "")

        if duties.is_work(title):
            # Add description.
            start = event.get("DTSTART").dt
            end = event.get("DTEND").dt

            # Get duty.
            duty = duties.get_duty(session, title, start)

            # Add description.
            description = duty.event_description()
            night_hours = duties.calculate_night_hours(start, end)
            description += "\n" + f"Night hours: '{night_hours:.2f}'"
            print(f"FINAL DESCRIPTION: {description}")
            event["DESCRIPTION"] = description

            # Add 1 day Alarm component before start of the duty.
            alarm_before = Alarm()
            alarm_before.add("action", "DISPLAY")
            alarm_before.add("trigger", datetime.timedelta(hours=-24))
            alarm_before.add("description", "Reminder: duty tommorow.")
            event.add_component(alarm_before)

            # Add location read from config.
            event["LOCATION"] = location.strip()

    session.close()

    with open(out_path, "wb") as f:
        f.write(cal.to_ical())

    print("Done.")


if __name__ == "__main__":
    main()
