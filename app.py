from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():

    timetable = []
    faculty = {}
    classrooms = {}
    subjects = []

    if request.method == "POST":

        # -------- GET FORM DATA --------
        faculty_names = request.form.getlist("faculty_name")
        faculty_available = request.form.getlist("available_slots")
        faculty_free = request.form.getlist("free_slots")

        room_names = request.form.getlist("room_name")
        room_capacity = request.form.getlist("room_capacity")

        subject_names = request.form.getlist("subject_name")
        subject_faculty = request.form.getlist("subject_faculty")
        subject_students = request.form.getlist("subject_students")

        time_slots_raw = request.form.get("time_slots", "")
        time_slots = [s.strip() for s in time_slots_raw.split(",") if s.strip() != ""]

        # -------- STORE FACULTY --------
        for i in range(len(faculty_names)):
            if faculty_names[i].strip() != "":
                faculty[faculty_names[i].strip()] = {
                    "available": [s.strip() for s in faculty_available[i].split(",") if s.strip() != ""],
                    "free": [s.strip() for s in faculty_free[i].split(",") if s.strip() != ""]
                }

        # -------- STORE CLASSROOMS --------
        for i in range(len(room_names)):
            if room_names[i].strip() != "" and room_capacity[i].strip() != "":
                try:
                    classrooms[room_names[i].strip()] = int(room_capacity[i])
                except ValueError:
                    pass

        # -------- STORE SUBJECTS --------
        for i in range(len(subject_names)):
            if subject_names[i].strip() != "" and subject_students[i].strip() != "":
                try:
                    subjects.append({
                        "name": subject_names[i].strip(),
                        "faculty": subject_faculty[i].strip(),
                        "students": int(subject_students[i])
                    })
                except ValueError:
                    pass

        # -------- SCHEDULING LOGIC --------
        used_faculty = set()
        used_rooms = {}

        for sub in subjects:
            fac = sub["faculty"]
            allocated = False

            if fac not in faculty:
                continue

            for slot in time_slots:
                slot = slot.strip()

                if slot in faculty[fac]["available"] and slot in faculty[fac]["free"]:

                    if (fac, slot) in used_faculty:
                        continue

                    for room, capacity in classrooms.items():

                        if capacity >= sub["students"] and used_rooms.get(slot) != room:

                            used_faculty.add((fac, slot))
                            used_rooms[slot] = room

                            timetable.append({
                                "Subject": sub["name"],
                                "Faculty": fac,
                                "Room": room,
                                "Time": slot
                            })

                            allocated = True
                            break

                if allocated:
                    break

    # -------- SEND DATA BACK TO HTML --------
    return render_template("index.html",
                           timetable=timetable,
                           faculty_data=[
                               {"name": k,
                                "available": ",".join(v["available"]),
                                "free": ",".join(v["free"])}
                               for k, v in faculty.items()
                           ],
                           room_data=[
                               {"name": k, "capacity": v}
                               for k, v in classrooms.items()
                           ],
                           subject_data=subjects)


if __name__ == "__main__":
    app.run(debug=True)