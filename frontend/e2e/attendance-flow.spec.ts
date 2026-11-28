import { expect, test } from "@playwright/test";

const apiBase = "http://127.0.0.1:18000/api/v1";
const password = process.env.SEED_DEFAULT_PASSWORD;

function todayInKolkata(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function randomTimeRange(): [string, string] {
  const startMinute = Math.floor(Math.random() * (24 * 60 - 45));
  const endMinute = startMinute + 45;
  const format = (value: number) =>
    `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
  return [format(startMinute), format(endMinute)];
}

test("teacher records two absences and the student sees updated attendance", async ({ page, request }) => {
  expect(password, "SEED_DEFAULT_PASSWORD must be set in the project .env").toBeTruthy();

  const studentLogin = await request.post(`${apiBase}/auth/login`, {
    data: { login_id: "1", password },
  });
  expect(studentLogin.ok()).toBeTruthy();
  const studentAuth = await studentLogin.json();
  const beforeResponse = await request.get(`${apiBase}/me/attendance/summary`, {
    headers: { Authorization: `Bearer ${studentAuth.access_token}` },
  });
  expect(beforeResponse.ok()).toBeTruthy();
  const beforeSummary = await beforeResponse.json();
  const targetCourse = beforeSummary.courses.find(
    (row: { course: { code: string; name: string } }) =>
      row.course.code === "CS501" && row.course.name === "Theory of Computation",
  );
  expect(targetCourse, "The seeded section should include CS501 Theory of Computation").toBeTruthy();

  const teacherLogin = await request.post(`${apiBase}/auth/login`, {
    data: { login_id: "FAC001", password },
  });
  expect(teacherLogin.ok()).toBeTruthy();
  const teacherAuth = await teacherLogin.json();
  const classesResponse = await request.get(`${apiBase}/teacher/classes`, {
    headers: { Authorization: `Bearer ${teacherAuth.access_token}` },
  });
  expect(classesResponse.ok()).toBeTruthy();
  const classes = await classesResponse.json();
  const targetClass = classes.find(
    (row: { course: { code: string; name: string }; section: { name: string; code: string } }) =>
      row.course.code === "CS501" &&
      row.course.name === "Theory of Computation" &&
      row.section.name === "A" &&
      row.section.code === "OIST-CSE-V-A",
  );
  expect(targetClass, "FAC001 should teach CS501 in Section A").toBeTruthy();

  await page.goto("/login");
  const loginIdInput = page.getByLabel("Login ID");
  await expect(loginIdInput).toBeVisible();
  await loginIdInput.fill("FAC001");
  await page.getByLabel("Password").fill(password!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/teacher$/);

  await page.goto("/teacher/sessions/new");
  const classSelect = page.locator("select").first();
  const sectionAOption = classSelect.locator("option").nth(1);
  await expect(sectionAOption).toContainText("CS501 · Theory of Computation");
  await expect(sectionAOption).toContainText("Section A");
  await classSelect.selectOption({ index: 1 });
  await page.locator('input[type="date"]').fill(todayInKolkata());
  const [startTime, endTime] = randomTimeRange();
  await page.locator('input[type="time"]').nth(0).fill(startTime);
  await page.locator('input[type="time"]').nth(1).fill(endTime);
  await page.getByPlaceholder("e.g. Normalization and keys").fill("M5 browser smoke check");
  await page.getByRole("button", { name: "Create session" }).click();
  await expect(page).toHaveURL(/\/teacher\/sessions\/\d+\/attendance$/);
  await expect(page.getByRole("heading", { name: "Section roster" })).toBeVisible();

  await page.getByRole("textbox", { name: /Absent roll numbers/ }).fill("1, 2");
  await expect(page.locator(".attendance-save-bar")).toContainText("Present 8 · Absent 2");
  await page.getByRole("button", { name: "Review and save" }).click();
  await expect(page.getByRole("dialog")).toContainText("Save 8 present, 2 absent?");
  await page.getByRole("button", { name: "Confirm save" }).click();
  await expect(page.getByText("Attendance saved")).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).first().click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Login ID").fill("1");
  await page.getByLabel("Password").fill(password!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/student$/);
  await page.goto("/student/attendance");

  const courseRow = page.locator("tbody tr").filter({
    has: page.getByText("Theory of Computation", { exact: true }),
  });
  await expect(courseRow).toContainText(
    `${targetCourse.present} / ${targetCourse.total + 1} present`,
  );

  const assignmentsResponse = await request.get(`${apiBase}/me/assignments`, {
    headers: { Authorization: `Bearer ${studentAuth.access_token}` },
  });
  expect(assignmentsResponse.ok()).toBeTruthy();
  const assignments = await assignmentsResponse.json();
  const pendingAssignment = assignments.find(
    (assignment: { status: string }) => assignment.status === "pending",
  );
  expect(pendingAssignment, "The seeded student should have a pending assignment").toBeTruthy();
  await page.goto("/student/assignments");
  const assignmentCard = page.locator(".assignment-card").filter({
    has: page.getByRole("heading", { name: pendingAssignment.title, exact: true }),
  });
  await assignmentCard.locator('input[type="file"]').setInputFiles({
    name: "practice.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7\nMock assignment submission"),
  });
  await expect(assignmentCard.locator(".assignment-status")).toContainText("submitted");
});
