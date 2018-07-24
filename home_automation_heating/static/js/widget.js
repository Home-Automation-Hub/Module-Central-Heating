window.app.registerModuleWebsocketEndpoint(function(key, data) {
    jQuery("#val-temperature").text(data["latest_reading"]);
}, "temperature", app.vars.heating_module_id);

window.app.registerModuleWebsocketEndpoint(function(key, data) {
    jQuery("#heating-state-off").addClass("d-none");
    jQuery("#heating-state-set-on").addClass("d-none");
    jQuery("#heating-state-running").addClass("d-none");

    var ch_set_on = data["ch_set_on"];
    var ch_running = data["ch_running"];

    if (!ch_set_on) {
        jQuery("#heating-state-off").removeClass("d-none");
    } else if (ch_running) {
        jQuery("#heating-state-running").removeClass("d-none");
    } else {
        jQuery("#heating-state-set-on").removeClass("d-none");
    }
}, "state", app.vars.heating_module_id);

window.app.registerModuleWebsocketEndpoint(function(key, data) {
    jQuery("#thermostat-temperature").text(data.value.toFixed(1));
}, "thermostat_updated", app.vars.heating_module_id);

window.app.registerModuleWebsocketEndpoint(function(key, data) {
    jQuery("#manual-controls-container div.alert").remove();
    if (data.state == "pending" || data.state == "running") {
        var alertClass = (data.state == "pending") ? "warning" : "success";
        
        jQuery("#manual-control-form").addClass("d-none");
        jQuery("#manual-control-form").removeClass("d-block");
        var alertHtml = '<div class="alert alert-' + alertClass + '">'
                 + data.message + '</div>';
        jQuery("#manual-controls-container").append(alertHtml);
        jQuery("#btn-cancel-manual-operation").removeClass("d-none");
    } else {
        jQuery("#manual-control-form").removeClass("d-none");
        jQuery("#manual-control-form").addClass("d-block");
        jQuery("#btn-cancel-manual-operation").addClass("d-none");
    }
}, "index_manual_message", app.vars.heating_module_id);

window.app.registerModuleWebsocketEndpoint(function(key, data) {
    if (data["control_mode"] == "manual") {
        jQuery("#manual-controls").removeClass("d-none");
        jQuery("#toggle-control-mode label").removeClass("active");
        jQuery("#toggle-control-mode input").prop("checked", false);
        jQuery("#control-mode-manual").addClass("active");
        jQuery("#control-mode-manual input").prop("checked", true);
    } else {
        jQuery("#manual-controls").addClass("d-none");
        jQuery("#toggle-control-mode label").removeClass("active");
        jQuery("#toggle-control-mode input").prop("checked", false);
        jQuery("#control-mode-timer").addClass("active");
        jQuery("#control-mode-timer input").prop("checked", true);
    }
}, "controlModeModified", app.vars.heating_module_id);

jQuery("#toggle-control-mode input").change(function() {
    var controlMode = jQuery(this).attr("data-mode");
    jQuery.ajax({
        url: app.vars.heating_module_base_path + "/action/save_control_mode/",
        type: "POST",
        data: JSON.stringify({mode: controlMode}),
        contentType: "application/json",
        dataType: "json",
        success: function(data) {
            if (!data.success) {
                alert(data.message);
            }
        }            
    });
});

jQuery("#select-manual-start-time").change(function() {
    if(jQuery(this).val() == "now") {
        jQuery("#manual-start-time").addClass("d-none");
    } else {
        jQuery("#manual-start-time").removeClass("d-none");
    }
});

jQuery("#select-manual-end-time").change(function() {
    if(jQuery(this).val() == "indefinitely") {
        jQuery("#manual-end-time").addClass("d-none");
    } else {
        jQuery("#manual-end-time").removeClass("d-none");
    }
});

jQuery("#submit-manual-control").click(function() {
    jQuery.ajax({
        url: app.vars.heating_module_base_path + "/action/store_manual_control/",
        type: "POST",
        data: JSON.stringify({
            startTimeType: jQuery("#select-manual-start-time").val(),
            startTime: jQuery("#manual-start-time").val(),
            endTimeType: jQuery("#select-manual-end-time").val(),
            endTime: jQuery("#manual-end-time").val()
        }),
        contentType: "application/json",
        dataType: "json",
        success: function(data) {
            if (!data.success) {
                alert(data.message);
            }
        }            
    });
});

jQuery("#btn-cancel-manual-operation").click(function() {
    jQuery.post(
        app.vars.heating_module_base_path + "/action/cancel_manual_operation/"
    );
});

jQuery(".btn-thermostat-adjust").click(function() {
    var direction = jQuery(this).attr("data-direction");
    jQuery.post(app.vars.heating_module_base_path + 
        "/action/change_thermostat/" + direction + "/");
});