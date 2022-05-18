// Copyright (c) 2022 - VKIST

function sse() {
    var source = new EventSource('/event_stream');
    source.onmessage = function(e) {
        get_data()
    };
}

var option = 'add'
function get_data() {
    fetch('/data')
    .then(res => res.json())
    .then(res => {
        $('#number_of_people').html(res['result']['number_of_people'])
        $('#number_of_current_checkin').html(res['result']['number_of_current_checkin'])
        $('#not_checkin').html(res['result']['number_of_people'] - res['result']['number_of_current_checkin'])

        timeline = ""
        for(i in res['result']['current_timeline']) {
            p = res['result']['current_timeline'][i]
            timeline +=
            `<tr>
                <td>
                    <div class="avatar-group">
                        <a href="#" class="avatar avatar-lg rounded-circle" data-toggle="tooltip" data-original-title="${p['name']}">
                            <img alt="Image placeholder" src="/image/${res['result']['secret_key']}/${p['image_id']}">
                        </a>
                    </div>
                </td>
                <td>
                    ${p['timestamp'].split('.')[0]}
                </td>
                <td class="${p['name'] != "Người lạ" ? "text-success" : "text-warning"}">
                    ${p['name']}
                </td>
            </tr>`
        }
        $('#timeline').html(timeline)

        strangers=""
        for(i in res['result']['strangers']) {
            p = res['result']['strangers'][i]
            strangers +=
            `<tr>
                <td>
                    <div class="avatar-group">
                        <a href="#" class="avatar avatar-lg rounded-circle" data-toggle="tooltip" data-original-title="Người lạ">
                            <img alt="Image placeholder" src="/image/${res['result']['secret_key']}/${p['image_id']}">
                        </a>
                    </div>
                </td>
                <td>
                    ${p['timestamp'].split('.')[0]}
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <button class="btn btn-sm btn-warning" type='submit' form='info-form' data-toggle="modal" data-target="#new-person" onclick="add_person('${res['result']['secret_key']}', '${p['image_id']}')">Đăng ký</button>
                    </div>
                </td>
            </tr>`
        }
        $('#strangers').html(strangers)

        current_checkin=""
        for(i in res['result']['current_checkin']) {
            p = res['result']['current_checkin'][i]
            current_checkin +=
            `
                <tr>
                    <th scope="row">
                        <div class="media align-items-center">
                            <div class="media-body">
                                <span class="name mb-0 text-sm">${parseInt(i)+1}</span>
                            </div>
                        </div>
                    </th>

                    <td class="budget">
                        ${p['name']}
                    </td>
                    
                    <td>
                        <div class="avatar-group">
                            <a href="#" class="avatar avatar-lg rounded-circle" data-toggle="tooltip" data-original-title="${p['name']}">
                                <img alt="${p['name']}" src="/image/${res['result']['secret_key']}/${p['image_id']}">
                            </a>
                        </div>
                    </td>
                
                    <td>
                        <span class="badge badge-dot mr-4">
                            <i class="${p['checkin'] ? 'bg-success' : 'bg-warning'}"></i>
                            <span class="status">${p['checkin'] ? 'Đã điểm danh' : 'Chưa điểm danh'}</span>
                        </span>
                    </td>

                    <td>
                        <span class="badge badge-dot mr-4">
                            <span class="status">${p['timestamp'].split('.')[0]}</span>
                        </span>
                    </td>
                </tr>
            `
        }
        $('#current_checkin').html(current_checkin)

        children_list=""
        for(i in res['result']['current_checkin']) {
            p = res['result']['current_checkin'][i]
            children_list +=
            `
                <tr>
                    <th scope="row">
                        <div class="media align-items-center">
                            <div class="media-body">
                                <span class="name mb-0 text-sm">${parseInt(i)+1}</span>
                            </div>
                        </div>
                    </th>

                    <td class="budget">
                        ${p['name']}
                    </td>
                    
                    <td>
                        <div class="avatar-group">
                            <a href="/list/${p['access_key']}" class="avatar avatar-lg rounded-circle" data-toggle="tooltip" data-original-title="${p['name']}">
                                <img alt="${p['name']}" src="/image/${res['result']['secret_key']}/${p['image_id']}">
                            </a>
                        </div>
                    </td>

					<td>
						<a href="/list/${p['access_key']}" class="btn btn-primary">Xem thống kê</a>
						<button class="btn btn-success new-event--add" data-toggle="modal" data-target="#change-name" onclick="change_person('${res['result']['secret_key']}', '${p['image_id']}', '${p['name']}', '${p['access_key']}')">Sửa tên</button>
					</td>
                   
                </tr>
            `
        }
        $('#children_list').html(children_list)

		children_list=`<option value="" disabled selected>Chọn người muốn thêm ảnh</option>`
        for(i in res['result']['current_checkin']) {
            p = res['result']['current_checkin'][i]
            children_list +=
			`
			<option value=${p['access_key']}>${p['name']}</option>
			`
		}
		$('#children_id').html(children_list)

		var labels = []
		var data = []
		for (i = 1; i <= moment().daysInMonth(); i++) {
			labels.push(('00'+i.toString()).slice(-2))
			data.push(0)
		}
		for(key in res['result']['checkin_data']) {
			data[parseInt(key.split('-')[2])-1] = res['result']['checkin_data'][key]
		}

    })
}

function add_person(secret_key, image_id) {
    $('#new-avatar').html(
    `<a href="#" class="avatar avatar-xxl rounded-circle" data-toggle="tooltip" data-original-title="Người lạ">
        <img alt="Image placeholder" src="/image/${secret_key}/${image_id}">
    </a>`)

    $('#new-footer').html(
    `
    <button type="submit" class="btn btn-primary new-event--add" onclick="add_request('${image_id}')" data-dismiss="modal">Thêm người</button>
    <button type="button" class="btn btn-link ml-auto" data-dismiss="modal">Đóng</button>
    `)
}

function add_request(image_id) {
	let body = ""
	if (option == 'add'){
		let new_name = $('#new_name').val()
		body = JSON.stringify({'image_id': image_id, 'name': new_name})
	} else {
		let access_key = $('#children_id').val()
		body = JSON.stringify({'image_id': image_id, 'access_key': access_key})
	}
    fetch('/facereg', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: body
    })
    .then(res => res.json())
    .then(res => {
		$('#new_name').val("")
        console.log(res)
    })
}

function change_person(secret_key, image_id, name, access_key) {
    $('#change-avatar').html(
    `<a href="#" class="avatar avatar-xxl rounded-circle" data-toggle="tooltip" data-original-title="${name}">
        <img alt="Image placeholder" src="/image/${secret_key}/${image_id}">
    </a>`)

	$('#change_name').val(name)

    $('#change-footer').html(
    `
    <button type="submit" class="btn btn-primary new-event--add" onclick="change_request('${access_key}')" data-dismiss="modal">Đổi tên</button>
    <button type="button" class="btn btn-link ml-auto" data-dismiss="modal">Đóng</button>
    `)
}

function change_request(access_key) {
    new_name = $('#change_name').val()
    fetch('/change_name', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({'access_key': access_key, 'name': new_name})
    })
    .then(res => res.json())
    .then(res => {
		$('#change_name').val("")
        console.log(res)
    })
}

$('input[type=radio][name=custom-radio-1]').change(function() {
    option = this.value
    if(this.value=='append') {
		$('#children_id').prop( "disabled", false )
		$('#new_name').prop( "disabled", true )
	} else {
		$('#children_id').prop( "disabled", true )
		$('#new_name').prop( "disabled", false )
	}
});

'use strict';

var Fullcalendar = (function() {

	// Variables

	var $calendar = $('[data-toggle="calendar"]');

	//
	// Methods
	//

	// Init
	function init($this) {
		// Full calendar options
		// For more options read the official docs: https://fullcalendar.io/docs

		options = {
			header: {
				right: '',
				center: '',
				left: ''
			},
			buttonIcons: {
				prev: 'calendar--prev',
				next: 'calendar--next'
			},
			theme: false,
			selectable: true,
			selectHelper: true,
			editable: true,
			events: events,

			dayClick: function(date) {
				var isoDate = moment(date).toISOString();
				$('#new-event').modal('show');
				$('.new-event--title').val('');
				$('.new-event--start').val(isoDate);
				$('.new-event--end').val(isoDate);
			},

			eventRender: function(event, eventElement) {
				if (event.imageurl) {
					eventElement.find("div.fc-content").prepend(`
					<div style="margin:3px; display:flex; justify-content:center, align-item:center">
						<div class="avatar-group">
							<a class="avatar avatar-sm rounded-circle" data-toggle="tooltip">
								<img src="${event.imageurl}">
							</a>
						</div>
					</div>
					`);
				}
			},

			viewRender: function(view) {
				var calendarDate = $this.fullCalendar('getDate');
				var calendarMonth = calendarDate.month();

				//Set data attribute for header. This is used to switch header images using css
				// $this.find('.fc-toolbar').attr('data-calendar-month', calendarMonth);

				//Set title in page header
				$('.fullcalendar-title').html(view.title);
			},

			// Edit calendar event action

			eventClick: function(event, element) {
				$('#edit-event input[value=' + event.className + ']').prop('checked', true);
				$('#edit-event').modal('show');
				$('.edit-event--id').val(event.id);
				$('.edit-event--title').val(event.title);
				$('.edit-event--description').val(event.description);
			}
		};

		// Initalize the calendar plugin
		$this.fullCalendar(options);


		//
		// Calendar actions
		//


		//Add new Event

		$('body').on('click', '.new-event--add', function() {
			var eventTitle = $('.new-event--title').val();

			// Generate ID
			var GenRandom = {
				Stored: [],
				Job: function() {
					var newId = Date.now().toString().substr(6); // or use any method that you want to achieve this string

					if (!this.Check(newId)) {
						this.Stored.push(newId);
						return newId;
					}
					return this.Job();
				},
				Check: function(id) {
					for (var i = 0; i < this.Stored.length; i++) {
						if (this.Stored[i] == id) return true;
					}
					return false;
				}
			};

			if (eventTitle != '') {
				$this.fullCalendar('renderEvent', {
					id: GenRandom.Job(),
					title: eventTitle,
					start: $('.new-event--start').val(),
					end: $('.new-event--end').val(),
					allDay: true,
					className: $('.event-tag input:checked').val()
				}, true);

				$('.new-event--form')[0].reset();
				$('.new-event--title').closest('.form-group').removeClass('has-danger');
				$('#new-event').modal('hide');
			} else {
				$('.new-event--title').closest('.form-group').addClass('has-danger');
				$('.new-event--title').focus();
			}
		});


		//Update/Delete an Event
		$('body').on('click', '[data-calendar]', function() {
			var calendarAction = $(this).data('calendar');
			var currentId = $('.edit-event--id').val();
			var currentTitle = $('.edit-event--title').val();
			var currentDesc = $('.edit-event--description').val();
			var currentClass = $('#edit-event .event-tag input:checked').val();
			var currentEvent = $this.fullCalendar('clientEvents', currentId);

			//Update
			if (calendarAction === 'update') {
				if (currentTitle != '') {
					currentEvent[0].title = currentTitle;
					currentEvent[0].description = currentDesc;
					currentEvent[0].className = [currentClass];

					console.log(currentClass);
					$this.fullCalendar('updateEvent', currentEvent[0]);
					$('#edit-event').modal('hide');
				} else {
					$('.edit-event--title').closest('.form-group').addClass('has-error');
					$('.edit-event--title').focus();
				}
			}

			//Delete
			if (calendarAction === 'delete') {
				$('#edit-event').modal('hide');

				// Show confirm dialog
				setTimeout(function() {
					swal({
						title: 'Are you sure?',
						text: "You won't be able to revert this!",
						type: 'warning',
						showCancelButton: true,
						buttonsStyling: false,
						confirmButtonClass: 'btn btn-danger',
						confirmButtonText: 'Yes, delete it!',
						cancelButtonClass: 'btn btn-secondary'
					}).then((result) => {
						if (result.value) {
							// Delete event
							$this.fullCalendar('removeEvents', currentId);

							// Show confirmation
							swal({
								title: 'Deleted!',
								text: 'The event has been deleted.',
								type: 'success',
								buttonsStyling: false,
								confirmButtonClass: 'btn btn-primary'
							});
						}
					})
				}, 200);
			}
		});


		//Calendar views switch
		$('body').on('click', '[data-calendar-view]', function(e) {
			e.preventDefault();

			$('[data-calendar-view]').removeClass('active');
			$(this).addClass('active');

			var calendarView = $(this).attr('data-calendar-view');
			$this.fullCalendar('changeView', calendarView);
		});


		//Calendar Next
		$('body').on('click', '.fullcalendar-btn-next', function(e) {
			e.preventDefault();
			$this.fullCalendar('next');
		});


		//Calendar Prev
		$('body').on('click', '.fullcalendar-btn-prev', function(e) {
			e.preventDefault();
			$this.fullCalendar('prev');
		});
	}


	//
	// Events
	//

	// Init
	if ($calendar.length) {
		init($calendar);
	}

})();

get_data()

sse()
