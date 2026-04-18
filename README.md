# OTHER LANGUAGES ARE IN OTHER BRANCHES


https://tesseract-ocr.github.io/tessdoc/#binaries get the binaries for your OS


pip install -r requirements.txt


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
