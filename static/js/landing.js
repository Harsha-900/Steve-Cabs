let currentIndex = 0;
const items = document.querySelectorAll('.carousel-item');
const total = items.length;
const inner = document.getElementById('carouselInner');

items.forEach(item => {
    const bg = item.dataset.bg;
    if (bg) item.style.backgroundImage = `url(${bg})`;
});

function showSlide(index) {
    if (index < 0) index = total - 1;
    if (index >= total) index = 0;
    currentIndex = index;
    inner.style.transform = `translateX(-${currentIndex * 100}%)`;
}
function nextSlide() { showSlide(currentIndex + 1); }
function prevSlide() { showSlide(currentIndex - 1); }

document.getElementById('nextBtn').addEventListener('click', nextSlide);
document.getElementById('prevBtn').addEventListener('click', prevSlide);
setInterval(nextSlide, 4000);
showSlide(0);