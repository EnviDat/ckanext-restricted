// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('restricted_popup', function ($) {
  return {
    initialize: function () {
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

ckan.module('restricted_create_json', function ($) {
  return {
    initialize: function() {
        $.proxyAll(this, /_on/);
        function create_json(){
          var restricted_json = {
            allowed_organizations: $('#field-restricted_allowed_orgs').val(),
            allowed_users: $('#field-restricted_allowed_users').val(),
            level: $('#field-level').val()
          };
          $('#field-restricted').val(JSON.stringify(restricted_json));
        }
        create_json()
        $('#field-restricted_allowed_orgs').on('change', function(event){
          create_json();
        });
        $('#field-restricted_allowed_users').on('change', function(event){
          create_json();
        });
        $('#field-level').on('change', function(event){
          create_json();
        });
    },
  };
});
