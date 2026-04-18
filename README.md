# OTHER LANGUAGES ARE IN OTHER BRANCHES


f12 console

document.querySelectorAll("input, textarea").forEach(el => {
    el.onpaste = null;
    el.onkeydown = null;
    el.oninput = null;
});


document.querySelectorAll("input, textarea").forEach(el => {
    const clone = el.cloneNode(true);
    el.parentNode.replaceChild(clone, el);
});
