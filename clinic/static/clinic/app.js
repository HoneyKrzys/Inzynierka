document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('patient');
    if (picker && document.getElementById('id_first_name')) picker.addEventListener('change', () => {
        const option = picker.selectedOptions[0];
        for (const key of ['first_name', 'second_name', 'last_name', 'phone', 'email', 'birth_date', 'address']) {
            if (option.dataset[key] !== undefined) document.getElementById('id_' + key).value = option.dataset[key];
        }
    });
    document.querySelectorAll('form').forEach(form => form.addEventListener('submit', event => {
        const button = event.submitter;
        const question = button?.dataset.confirmButton || form.dataset.confirm;
        if (question && !window.confirm(question)) {
            event.preventDefault();
            return;
        }
        if (form.dataset.submitting) {
            event.preventDefault();
            return;
        }
        if (button?.dataset.busy) {
            form.dataset.submitting = 'true';
            button.textContent = button.dataset.busy;
            button.setAttribute('aria-busy', 'true');
            button.classList.add('busy');
        }
    }));
});

document.addEventListener('DOMContentLoaded', () => {
    const select = document.querySelector('[data-autocomplete="patients"]');
    if (!select) return;
    const options = Array.from(select.options).filter(option => option.value);
    const wrapper = document.createElement('div');
    wrapper.className = 'patient-combobox';
    const input = document.createElement('input');
    input.id = 'patient-autocomplete';
    input.type = 'text';
    input.required = select.required;
    input.autocomplete = 'off';
    input.placeholder = 'Zacznij wpisywać imię lub nazwisko…';
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', 'patient-suggestions');
    const list = document.createElement('div');
    list.id = 'patient-suggestions';
    list.className = 'patient-suggestions';
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    select.before(wrapper);
    wrapper.append(input, list);
    document.querySelector('label[for="patient"]').htmlFor = input.id;
    select.hidden = true;
    select.required = false;
    input.value = select.value ? select.selectedOptions[0].textContent.trim() : '';
    let matches = [],
        active = -1;
    const normalize = value => value.toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l');

    function close() {
        list.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
        active = -1;
    }

    function choose(option) {
        select.value = option.value;
        input.value = option.textContent.trim();
        input.setCustomValidity('');
        select.dispatchEvent(new Event('change', {
            bubbles: true
        }));
        close();
    }

    function show() {
        const words = normalize(input.value).trim().split(/\s+/).filter(Boolean);
        matches = options.filter(option => words.every(word => normalize(option.textContent).includes(word)));
        list.replaceChildren();
        active = -1;
        input.removeAttribute('aria-activedescendant');
        matches.forEach((option, index) => {
            const row = document.createElement('div');
            row.id = 'patient-option-' + index;
            row.setAttribute('role', 'option');
            row.setAttribute('aria-selected', 'false');
            row.textContent = option.textContent.trim();
            row.addEventListener('mousedown', event => event.preventDefault());
            row.addEventListener('click', () => choose(option));
            list.append(row);
        });
        if (!matches.length) {
            const empty = document.createElement('div');
            empty.textContent = 'Brak pasujących pacjentów';
            empty.setAttribute('role', 'status');
            list.append(empty);
        }
        list.hidden = false;
        input.setAttribute('aria-expanded', 'true');
    }
    input.addEventListener('input', () => {
        if (select.value && document.getElementById('id_first_name')) {
            for (const key of ['first_name', 'second_name', 'last_name', 'phone', 'email', 'birth_date', 'address']) document.getElementById('id_' + key).value = '';
        }
        select.value = '';
        input.setCustomValidity(input.value.trim() || input.required ? 'Wybierz pacjenta z podpowiedzi.' : '');
        show();
    });
    input.addEventListener('focus', show);
    input.addEventListener('blur', close);
    input.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            close();
            return;
        }
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            if (list.hidden) show();
            if (!matches.length) return;
            active = (active + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length;
            Array.from(list.children).forEach((row, index) => row.setAttribute('aria-selected', String(index === active)));
            input.setAttribute('aria-activedescendant', list.children[active].id);
            list.children[active].scrollIntoView({
                block: 'nearest'
            });
        } else if (event.key === 'Enter' && !list.hidden) {
            event.preventDefault();
            if (active >= 0) choose(matches[active]);
            else if (matches.length === 1) choose(matches[0]);
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const stages = Array.from(document.querySelectorAll('[data-visit-stage]'));
    if (!stages.length) return;
    const buttons = document.querySelectorAll('[data-stage-target]');
    const finalSections = document.querySelectorAll('[data-final-stage]');
    const key = 'interview-stage:' + location.pathname;

    function show(index, scroll = false) {
        stages.forEach((stage, i) => {
            stage.hidden = i !== index;
        });
        finalSections.forEach(section => {
            section.hidden = index !== stages.length - 1;
        });
        buttons.forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.stageTarget) === index)));
        try {
            sessionStorage.setItem(key, String(index));
        } catch (_) {}
        if (scroll) {
            const top = document.getElementById('interview-start');
            top.focus({
                preventScroll: true
            });
            top.scrollIntoView({
                behavior: 'instant',
                block: 'start'
            });
        }
    }
    buttons.forEach(button => button.addEventListener('click', () => show(Number(button.dataset.stageTarget), true)));
    document.getElementById('visit-form').addEventListener('invalid', event => {
        const stage = event.target.closest('[data-visit-stage]');
        if (stage) show(Number(stage.dataset.visitStage));
        else if (event.target.closest('[data-final-stage]')) show(stages.length - 1);
    }, true);
    const errorStage = stages.findIndex(stage => stage.querySelector('.errorlist'));
    let saved = 0;
    try {
        saved = Number(sessionStorage.getItem(key));
    } catch (_) {}
    if (!Number.isInteger(saved) || saved < 0 || saved >= stages.length) saved = 0;
    const finalError = Array.from(finalSections).some(section => section.querySelector('.errorlist'));
    show(errorStage >= 0 ? errorStage : finalError ? stages.length - 1 : saved);
});

document.addEventListener('DOMContentLoaded', () => {
    const menu = document.getElementById('document-types');
    if (!menu) return;
    const toggles = document.querySelectorAll('[data-document-toggle]');
    toggles.forEach(button => button.addEventListener('click', () => {
        menu.hidden = !menu.hidden;
        toggles.forEach(toggle => toggle.setAttribute('aria-expanded', String(!menu.hidden)));
        if (!menu.hidden) menu.scrollIntoView({
            block: 'nearest'
        });
    }));
});

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('document-form');
    if (!form) return;
    form.elements.kind?.addEventListener('change', () => {
        const kind = form.elements.kind.value;
        if (kind) {
            const url = new URL(window.location.href);
            url.searchParams.set('kind', kind);
            if (form.elements.patient.value) url.searchParams.set('patient', form.elements.patient.value);
            window.location.href = url.toString();
        }
    });
    const patients = JSON.parse(document.getElementById('document-patients').textContent);
    const facilities = JSON.parse(document.getElementById('document-facilities').textContent);

    function set(name, value, overwrite) {
        const field = form.elements.namedItem(name);
        if (field && (overwrite || !field.value)) field.value = value || '';
    }

    function patientChanged(overwrite) {
        const p = patients[form.elements.patient.value] || {};
        set('patient_name', p.display, true);
        set('patient_pesel', p.pesel, true);
        set('patient_birth', p.birth, true);
        set('patient_address', p.address, overwrite);
        const visit = form.elements.visit;
        const previous = overwrite ? '' : visit.value;
        visit.replaceChildren(new Option('Brak powiązanej wizyty', ''));
        for (const item of p.visits || []) visit.add(new Option(item.label, item.id));
        visit.value = Array.from(visit.options).some(option => option.value === previous) ? previous : '';

    }

    function facilityChanged(overwrite) {
        const a = facilities[form.elements.agreement?.value] || {};
        set('facility_address', a.address, overwrite);
        set('facility_phone', a.phone, overwrite);
    }
    form.elements.patient.addEventListener('change', () => patientChanged(true));
    form.elements.agreement?.addEventListener('change', () => facilityChanged(true));
    patientChanged(false);
    facilityChanged(false);
});

document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('drug-picker');
    if (!picker) return;
    const input = document.getElementById('id_drug_search');
    const hidden = document.getElementById('id_package_id');
    const selected = document.getElementById('drug-selected');
    const options = document.getElementById('drug-options');
    input.after(picker);
    input.setAttribute('aria-describedby', 'drug-selected');
    let timer, version = 0;
    input.addEventListener('input', () => {
        hidden.value = '';
        selected.textContent = '';
        options.replaceChildren();
        clearTimeout(timer);
        const current = ++version;
        if (input.value.trim().length < 2) return;
        timer = setTimeout(async () => {
            selected.textContent = 'Wyszukiwanie…';
            try {
                const response = await fetch(picker.dataset.url + '?q=' + encodeURIComponent(input.value.trim()));
                if (!response.ok) throw new Error();
                const data = await response.json();
                if (current !== version) return;
                selected.textContent = data.results.length ? 'Wybierz lek i opakowanie (maksymalnie 30 wyników):' : 'Nie znaleziono leku.';
                for (const item of data.results) {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'button outline';
                    button.style.cssText = 'display:block;width:100%;text-align:left;margin:6px 0;white-space:normal';
                    button.textContent = item.label;
                    button.addEventListener('click', () => {
                        hidden.value = item.id;
                        input.value = item.label;
                        selected.textContent = 'Wybrano: ' + item.label;
                        options.replaceChildren();
                    });
                    options.append(button);
                }
            } catch (_) {
                if (current === version) selected.textContent = 'Nie udało się pobrać leków. Spróbuj ponownie.';
            }
        }, 250);
    });
});
