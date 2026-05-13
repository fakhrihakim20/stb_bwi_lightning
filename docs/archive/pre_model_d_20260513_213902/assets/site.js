/* Reveal-on-scroll + nav interactions */

// Mobile nav toggle
const navToggle = document.querySelector(".nav-toggle");
if (navToggle) {
  navToggle.addEventListener("click", () => {
    const open = navToggle.getAttribute("aria-expanded") === "true";
    navToggle.setAttribute("aria-expanded", String(!open));
  });
  // Close after click on a link
  document.querySelectorAll(".nav-links a").forEach(a => {
    a.addEventListener("click", () => {
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

// IntersectionObserver reveal
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add("in");
      io.unobserve(e.target);
    }
  });
}, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });

document.querySelectorAll(".reveal").forEach(el => io.observe(el));

// Active-section highlighting on scroll
const sections = ["summary","problem","data","method","forecast","hotspots","caveats","downloads"];
const navAnchors = {};
sections.forEach(id => {
  navAnchors[id] = document.querySelector(`.nav-links a[href="#${id}"]`);
});
const sectionIO = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      Object.values(navAnchors).forEach(a => a && a.classList.remove("active"));
      const a = navAnchors[e.target.id];
      if (a) a.classList.add("active");
    }
  });
}, { rootMargin: "-40% 0px -55% 0px", threshold: 0 });
sections.forEach(id => {
  const s = document.getElementById(id);
  if (s) sectionIO.observe(s);
});
