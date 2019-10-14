// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('restricted_popup', function ($) {
  return {
    initialize: function () {
      console.log("Initialize", this.el);
      this.el.popover({
        title: this.options.title,
        content: this.options.content,
		    html: true,
        placement: 'left',
        trigger: 'hover'
      });
    }
  };
});

ckan.module('restricted_hide', function ($) {
  return {
    initialize: function () {

      if(this.el.val() == "public"){
	$(document).ready(function (){
	  $('#s2id_field-restricted_allowed_orgs').parent().parent().hide();
	  $('#s2id_field-restricted_allowed_users').parent().parent().hide();
	});
      }
      this.el.change(function () {
	if(this.value == "public"){
	  $('#s2id_field-restricted_allowed_orgs').parent().parent().hide();
	  $('#s2id_field-restricted_allowed_users').parent().parent().hide();
	}else{
	  $('#s2id_field-restricted_allowed_orgs').parent().parent().show();
	  $('#s2id_field-restricted_allowed_users').parent().parent().show();

	}
      });
    }
  };
});
