(function () {
    'use strict';

    console.log('[BookingLance] JS loaded at', new Date().toISOString());

    document.addEventListener('DOMContentLoaded', function () {
        console.log('[BookingLance] DOMContentLoaded fired');

        var slotInput = document.getElementById('bl-slot-input');
        var reviewBtn = document.getElementById('bl-review-btn');

        console.log('[BookingLance] slotInput found:', !!slotInput);
        console.log('[BookingLance] reviewBtn found:', !!reviewBtn);

        var directBtns = document.querySelectorAll('.bl-slot-btn');
        console.log('[BookingLance] .bl-slot-btn elements found at DOMContentLoaded:', directBtns.length);

        if (reviewBtn) {
            reviewBtn.disabled = true;
            reviewBtn.style.opacity = '0.5';
            reviewBtn.style.cursor = 'not-allowed';
        }

        // Event delegation on document
        document.addEventListener('click', function (e) {
            console.log('[BookingLance] click on:', e.target.tagName, e.target.className);

            var btn = e.target.closest('.bl-slot-btn');
            console.log('[BookingLance] closest .bl-slot-btn:', btn);

            if (!btn) return;

            console.log('[BookingLance] Slot clicked! data-slot-id:', btn.getAttribute('data-slot-id'));

            e.preventDefault();
            e.stopPropagation();

            document.querySelectorAll('.bl-slot-btn').forEach(function (b) {
                b.classList.remove('selected');
                b.removeAttribute('style');
            });

            btn.classList.add('selected');
            btn.setAttribute('style',
                'border-color: #9c27b0 !important;' +
                'background: rgba(156,39,176,0.12) !important;' +
                'color: #9c27b0 !important;' +
                'font-weight: 600 !important;' +
                'box-shadow: 0 0 0 2px rgba(156,39,176,0.2) !important;'
            );

            if (slotInput) {
                slotInput.value = btn.getAttribute('data-slot-id');
                console.log('[BookingLance] slotInput value set to:', slotInput.value);
            }

            if (reviewBtn) {
                reviewBtn.disabled = false;
                reviewBtn.removeAttribute('style');
                reviewBtn.textContent = 'Continue to Review';
                console.log('[BookingLance] reviewBtn enabled');
            }
        });

        console.log('[BookingLance] Event delegation attached to document');
    });
})();
