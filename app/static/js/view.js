// js/view.js

const items = [
    { 
        code: "CITS3200", 
        name: "Professional Computing",
        type: "Units",
        credit: 6,
        coordinator: "Associate Professor Michael Wise",
        levelOfStudy: "Undergraduate",
        school: "Physics, Mathematics and Computing",
        field: "Management and Commerce",
        level: 3,
        availability: "Semester 2",
        location: "UWA (Perth)"
    },
    { 
        code: "PHIL2008", 
        name: "Philosophy Machine Minds",
        type: "Units",
        credit: 6,
        coordinator: "Dr Chris Letheby",
        levelOfStudy: "Undergraduate",
        school: "Humanities",
        field: "Society and Culture",
        level: 2,
        availability: "Semester 2",
        location: "UWA (Perth)"
    }
];

const params = new URLSearchParams(window.location.search);
const unitCode = params.get("code");

let unit = items.find(i => i.code === unitCode);

function renderUnitDetails() {
    if (unit) {
        document.getElementById("unitTitle").textContent = `${unit.name} [${unit.code}]`;
        document.getElementById("unitDetails").innerHTML = `
            <strong>Type:</strong> ${unit.type} <br>
            <strong>Credit Points:</strong> ${unit.credit} <br>
            <strong>Coordinator(s):</strong> ${unit.coordinator} <br>
            <strong>Level of Study:</strong> ${unit.levelOfStudy} <br>
            <strong>School:</strong> ${unit.school} <br>
            <strong>Field of Education:</strong> ${unit.field} <br>
            <strong>Level:</strong> ${unit.level} <br>
            <strong>Availability:</strong> ${unit.availability} <br>
            <strong>Location:</strong> ${unit.location}
        `;
    } else {
        document.getElementById("unitTitle").textContent = "Unit not found";
    }
}

renderUnitDetails();

// Edit button functionality
const editBtn = document.getElementById("editBtn");
const editForm = document.getElementById("editForm");
const saveBtn = document.getElementById("saveBtn");
const cancelBtn = document.getElementById("cancelBtn");

editBtn.addEventListener("click", () => {
    if (!unit) return;
    document.getElementById("editName").value = unit.name;
    document.getElementById("editCoordinator").value = unit.coordinator;
    document.getElementById("editAvailability").value = unit.availability;

    editForm.classList.remove("d-none");
    editBtn.classList.add("d-none");
});

cancelBtn.addEventListener("click", () => {
    editForm.classList.add("d-none");
    editBtn.classList.remove("d-none");
});

saveBtn.addEventListener("click", () => {
    unit.name = document.getElementById("editName").value;
    unit.coordinator = document.getElementById("editCoordinator").value;
    unit.availability = document.getElementById("editAvailability").value;

    renderUnitDetails();

    editForm.classList.add("d-none");
    editBtn.classList.remove("d-none");
});
