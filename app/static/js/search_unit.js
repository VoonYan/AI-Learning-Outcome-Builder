// js/search_unit.js

document.addEventListener("DOMContentLoaded", function() {
    const viewBtn = document.getElementById("viewBtn");
    const resultsSection = document.getElementById("resultsSection");
    const resultsList = document.getElementById("resultsList");

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

    function renderResults(data) {
        resultsList.innerHTML = "";
        data.forEach(item => {
            const li = document.createElement("li");
            li.classList.add("mb-3", "p-3", "border", "rounded", "bg-light");

            const strongLink = document.createElement("a");
            strongLink.href = `/view?code=${encodeURIComponent(item.code)}`;
            strongLink.textContent = `${item.name} [${item.code}]`;
            strongLink.style.fontWeight = "bold";
            strongLink.style.textDecoration = "none";
            strongLink.style.color = "black";
            strongLink.style.cursor = "pointer";

            strongLink.addEventListener("mouseenter", () => {
                strongLink.style.color = "blue";
                strongLink.style.textDecoration = "underline";
            });
            strongLink.addEventListener("mouseleave", () => {
                strongLink.style.color = "black";
                strongLink.style.textDecoration = "none";
            });

            const details = document.createElement("div");
            details.innerHTML = `
                Type: ${item.type} | Credit points: ${item.credit} | Coordinator(s): ${item.coordinator}<br>
                Level of study: ${item.levelOfStudy} | School: ${item.school} | Field of Education: ${item.field}<br>
                Level: ${item.level} | Availability: ${item.availability} | Location: ${item.location}
            `;

            li.appendChild(strongLink);
            li.appendChild(document.createElement("br"));
            li.appendChild(details);

            resultsList.appendChild(li);
        });
    }

    viewBtn.addEventListener("click", function() {
        resultsSection.classList.remove("d-none");
        renderResults(items);
    });

    document.querySelector(".form-select.w-auto").addEventListener("change", function() {
        const sortBy = this.value;
        let sorted = [...items];

        if (sortBy === "unitcode") {
            sorted.sort((a, b) => a.code.localeCompare(b.code));
        } else if (sortBy === "unitlevel") {
            sorted.sort((a, b) => {
                const levelA = parseInt(a.code.match(/\d+/)[0].charAt(0));
                const levelB = parseInt(b.code.match(/\d+/)[0].charAt(0));
                return levelA - levelB;
            });
        }

        renderResults(sorted);
    });
});
