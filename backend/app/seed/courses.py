"""Editable CSE Semester V course catalogue and section-to-faculty mapping."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CourseSpec:
    code: str
    name: str
    kind: str
    faculty_a: str
    faculty_b: str


FACULTY = {
    "FAC001": ("Demo Faculty One", "Assistant Professor"),
    "FAC002": ("Demo Faculty Two", "Assistant Professor"),
    "FAC003": ("Demo Faculty Three", "Assistant Professor"),
    "FAC004": ("Demo Faculty Four", "Assistant Professor"),
    "FAC005": ("Demo Faculty Five", "Lab Instructor"),
    "FAC006": ("Demo Faculty Six", "Project Mentor"),
}

COURSES = (
    CourseSpec("CS501", "Theory of Computation", "theory", "FAC001", "FAC001"),
    CourseSpec("CS502", "Database Management Systems", "theory", "FAC002", "FAC002"),
    CourseSpec("CS503(A)", "Data Analytics", "theory", "FAC003", "FAC004"),
    CourseSpec("CS504(A)", "Internet and Web Technology", "theory", "FAC004", "FAC003"),
    CourseSpec("CS502", "DBMS Lab", "practical", "FAC005", "FAC002"),
    CourseSpec("CS501", "Theory of Computation Lab", "practical", "FAC005", "FAC001"),
    CourseSpec("CS505", "Linux Lab", "practical", "FAC006", "FAC006"),
    CourseSpec("CS508", "Minor Project-I", "project", "FAC006", "FAC006"),
)

HISTORY_COURSE_KEYS = {
    ("CS503(A)", "Data Analytics"),
    ("CS504(A)", "Internet and Web Technology"),
}
