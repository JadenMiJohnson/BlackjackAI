async function buildNav() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;

    let loggedIn = false;
    let username = '';
    try {
        const res = await fetch('/api/auth/me');
        const data = await res.json();
        loggedIn = data.logged_in;
        username = data.username || '';
    } catch (e) {}

    const path = window.location.pathname;

    let links = '';
    links += navLink('/play', 'Play Blackjack', path);
    links += navLink('/rules', 'Rules', path);
    links += navLink('/hilo', 'Hi-Lo', path);
    links += navLink('/how-to-play', 'How to Play', path);

    if (loggedIn) {
        links += navLink('/dashboard', 'Dashboard', path);
        links += '<a href="#" onclick="doLogout()" class="nav-logout">Logout</a>';
    } else {
        links += navLink('/login', 'Login', path);
        links += navLink('/register', 'Register', path);
    }

    navbar.innerHTML =
        '<div class="navbar-inner">' +
        '<a href="/" class="navbar-brand">Agent B21</a>' +
        '<div class="navbar-links">' + links + '</div>' +
        '</div>';
}

function navLink(href, text, currentPath) {
    const active = currentPath === href ? ' class="nav-active"' : '';
    return '<a href="' + href + '"' + active + '>' + text + '</a>';
}

async function doLogout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
}

buildNav();
