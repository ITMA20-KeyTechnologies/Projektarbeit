'use strict';

let container_element;
let person_count_element;

let current_capacity = null;
let current_visualisation = null;


function get_fill_level() {
    fetch('/capacity')
        .then(response => {
            return response.json()
        })
        .then(data => {
            const state = data['state'];
            if (state === 'ok') {
                const capacity = data['capacity'];
                if (capacity !== current_capacity) {
                    current_capacity = capacity;
                    person_count_element.innerHTML = capacity;
                    person_count_element.classList.add('start_animation');
                }

                const visualisation = data['visualisation'];
                if (visualisation !== current_visualisation) {
                    current_visualisation = visualisation;
                    container_element.setAttribute('data-visualisation', visualisation)
                }
            } else {
                console.error('An error occurred: ' + data['message']);
                
            }
        })
        .finally(() => window.setTimeout(get_fill_level, 1000));
}

function init() {
    container_element = document.getElementById('container');
    person_count_element = document.getElementById('person_count');

    person_count_element.addEventListener('animationend', function () {
        person_count_element.classList.remove('start_animation');
    });

    get_fill_level();
}

window.addEventListener('load', init);