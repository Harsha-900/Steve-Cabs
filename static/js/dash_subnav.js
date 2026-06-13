/* # Sticky section nav: smooth scroll + highlight link for visible section */
(function () {
    document.addEventListener('DOMContentLoaded', function () {
        var nav = document.querySelector('.dash-subnav-scroll');
        if (!nav) return;

        var links = Array.prototype.slice.call(nav.querySelectorAll('a[href^="#"]'));
        if (!links.length) return;

        links.forEach(function (a) {
            a.addEventListener('click', function (e) {
                var id = a.getAttribute('href');
                if (id.length < 2) return;
                var el = document.querySelector(id);
                if (!el) return;
                e.preventDefault();
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                links.forEach(function (x) { x.classList.remove('is-active'); });
                a.classList.add('is-active');
            });
        });

        var sections = links.map(function (a) {
            return document.querySelector(a.getAttribute('href'));
        }).filter(Boolean);

        if (!sections.length || !window.IntersectionObserver) return;

        var obs = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (en) {
                    if (!en.isIntersecting || en.intersectionRatio < 0.2) return;
                    var id = '#' + en.target.id;
                    links.forEach(function (a) {
                        a.classList.toggle('is-active', a.getAttribute('href') === id);
                    });
                });
            },
            { rootMargin: '-12% 0px -55% 0px', threshold: [0, 0.15, 0.35] }
        );

        sections.forEach(function (s) { obs.observe(s); });
    });
})();
