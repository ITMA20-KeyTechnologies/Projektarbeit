'use strict';

function get_current_config() {
    hide_error();
    const fetch_init = {
        method: 'GET',
    };
    fetch('/current_config', fetch_init)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server answer: ${response.status} - ${response.statusText}`);
            }
            return response.json();
        })
        .then(config => document.getElementById('config').innerText = JSON.stringify(config, null, 2))
        .catch(error => show_error(error));
}

function set_current_config() {
    hide_error();
    const fetch_init = {
        method: 'POST',
        body: document.getElementById('config').innerText
    };
    fetch('/current_config', fetch_init)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server answer: ${response.status} - ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data['state'] === 'error') {
                throw new Error(data['message']);
            } else {
                get_current_config();
            }
        })
        .catch(error => show_error(error));
}

function send_command(cmd, data = null) {
    hide_error();
    const fetch_init = {
        method: 'POST',
        body: JSON.stringify({'cmd': cmd, 'data': data})
    };
    fetch('/cmd', fetch_init)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server answer: ${response.status} - ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data['state'] === 'error') {
                throw new Error(data['message']);
            } else {
                get_current_config();
            }
        })
        .catch(error => show_error(error));
}

function show_error(message) {
    let error_element = document.getElementById('error');
    error_element.innerHTML = message;
    error_element.classList.add('visible');
}

function hide_error() {
    let error_element = document.getElementById('error');
    error_element.classList.remove('visible');
}


function init() {
    get_current_config();
    document.getElementById('save_config_button').addEventListener('click', set_current_config);

    document.getElementById('increment_fill_level_button').addEventListener('click', function () {
        send_command('increment')
    });

    document.getElementById('decrement_fill_level_button').addEventListener('click', function () {
        send_command('decrement')
    });

    document.getElementById('reset_fill_level_button').addEventListener('click', function () {
        send_command('reset')
    });

}


window.addEventListener('load', init);