// let autocomplete;

// function initAutoComplete(){
// autocomplete = new google.maps.places.Autocomplete(
//     document.getElementById('id_address'),
//     {
//         types: ['geocode', 'establishment'],
//         //default in this app is "IN" - add your country code
//         componentRestrictions: {'country': ['ng']},
//     })
// // function to specify what should happen when the prediction is clicked
// autocomplete.addListener('place_changed', onPlaceChanged);
// }

// function onPlaceChanged (){
//     var place = autocomplete.getPlace();

//     // User did not select the prediction. Reset the input field or alert()
//     if (!place.geometry){
//         document.getElementById('id_address').placeholder = "Start typing...";
//     }
//     else{
//         // console.log('place name=>', place.name)
//     }

//     // get the address components and assign them to the fields
//     // console.log(place);
//     var geocoder = new google.maps.Geocoder()
//     var address = document.getElementById('id_address').value

//     geocoder.geocode({'address': address}, function(results, status){
//         // console.log('results=>', results)
//         // console.log('status=>', status)
//         if(status == google.maps.GeocoderStatus.OK){
//             var latitude = results[0].geometry.location.lat();
//             var longitude = results[0].geometry.location.lng();

//             // console.log('lat=>', latitude);
//             // console.log('long=>', longitude);
//             $('#id_latitude').val(latitude);
//             $('#id_longitude').val(longitude);

//             $('#id_address').val(address);
//         }
//     });

//     // loop through the address components and assign other address data
//     console.log(place.address_components);
//     for(var i=0; i<place.address_components.length; i++){
//         for(var j=0; j<place.address_components[i].types.length; j++){
//             // get country
//             if(place.address_components[i].types[j] == 'country'){
//                 $('#id_country').val(place.address_components[i].long_name);
//             }
//             // get state
//             if(place.address_components[i].types[j] == 'administrative_area_level_1'){
//                 $('#id_state').val(place.address_components[i].long_name);
//             }
//             // get city
//             if(place.address_components[i].types[j] == 'locality'){
//                 $('#id_city').val(place.address_components[i].long_name);
//             }
//             // get pincode
//             if(place.address_components[i].types[j] == 'postal_code'){
//                 $('#id_pin_code').val(place.address_components[i].long_name);
//             }else{
//                 $('#id_pin_code').val("");
//             }
//         }
//     }

// }


$(document).ready(function(){
    // add to cart
    $('.add_to_cart').on('click', function(e){
        e.preventDefault();
        
        item_id = $(this).attr('data-id');
        url = $(this).attr('data-url');
        
       
        $.ajax({
            type: 'GET',
            url: url,
            success: function(response){
                console.log(response)
                if(response.status == 'login_required'){
                    swal(response.message, '', 'info').then(function(){
                        window.location = '/accounts';
                    })
                }else if(response.status == 'Failed'){
                    swal(response.message, '', 'error')
                }else{
                    $('#cart_counter').html(response.cart_counter['cart_count']);
                    $('#ses-'+item_id).html(response.ses);

                    // subtotal, tax and grand total
                    applyCartAmounts(
                        response.cart_amount['subtotal'],
                        response.cart_amount['tax_dict'],
                        response.cart_amount['grand_total']
                    )
                }
            }
        })
    })


    // place the cart item quantity on load
    $('.item_ses').each(function(){
        var the_id = $(this).attr('id')
        var ses = $(this).attr('data-ses')
        $('#'+the_id).html(ses)
    })

    // decrease cart
    $('.decrease_cart').on('click', function(e){
        e.preventDefault();
        
        food_id = $(this).attr('data-id');
        url = $(this).attr('data-url');
        cart_id = $(this).attr('id');
        
        
        $.ajax({
            type: 'GET',
            url: url,
            success: function(response){
                console.log(response)
                if(response.status == 'login_required'){
                    swal(response.message, '', 'info').then(function(){
                        window.location = '/accounts';
                    })
                }else if(response.status == 'Failed'){
                    swal(response.message, '', 'error')
                }else{
                    
                    $('#cart_counter').html(response.cart_counter['cart_count']);
                    $('#ses-'+item_id).html(response.ses);

                    applyCartAmounts(
                        response.cart_amount['subtotal'],
                        response.cart_amount['tax_dict'],
                        response.cart_amount['grand_total']
                    )

                    if(window.location.pathname == '/cart/'){
                        removeCartItem(response.ses, cart_id);
                        checkEmptyCart();
                    }
                    
                } 
            }
        })
    })


    // DELETE CART ITEM
    $('.delete_cart').on('click', function(e){
        e.preventDefault();
        
        cart_id = $(this).attr('data-id');
        url = $(this).attr('data-url');
        
        
        $.ajax({
            type: 'GET',
            url: url,
            success: function(response){
                console.log(response)
                if(response.status == 'Failed'){
                    swal(response.message, '', 'error')
                }else{
                    $('#cart_counter').html(response.cart_counter['cart_count']);
                    swal(response.status, response.message, "success")

                    applyCartAmounts(
                        response.cart_amount['subtotal'],
                        response.cart_amount['tax_dict'],
                        response.cart_amount['grand_total']
                    )

                    removeCartItem(0, cart_id);
                    checkEmptyCart();
                } 
            }
        })
    })


    // delete the cart element if the ses is 0
    function removeCartItem(cartItemQty, cart_id){
            if(cartItemQty <= 0){
                // remove the cart item element
                document.getElementById("cart-item-"+cart_id).remove()
            }
        
    }

    // Check if the cart is empty
    function checkEmptyCart(){
        var cart_counter = document.getElementById('cart_counter').innerHTML
        if(cart_counter == 0){
            document.getElementById("empty-cart").style.display = "block";
        }
    }


    // apply cart amounts
    function applyCartAmounts(subtotal, tax_dict, grand_total){
        if(window.location.pathname == '/cart/'){
            $('#subtotal').html(subtotal)
            $('#total').html(grand_total)

            console.log(tax_dict)
            for(key1 in tax_dict){
                console.log(tax_dict[key1])
                for(key2 in tax_dict[key1]){
                    // console.log(tax_dict[key1][key2])
                    $('#tax-'+key1).html(tax_dict[key1][key2])
                }
            }
        }
    }

    // ADD OPENING HOUR
    $('.add_hour').on('click', function(e){
        e.preventDefault();
        var day = document.getElementById('id_day').value
        var from_hour = document.getElementById('id_from_hour').value
        var to_hour = document.getElementById('id_to_hour').value
        var is_offline = document.getElementById('id_is_offline').checked
        var csrf_token = $('input[name=csrfmiddlewaretoken]').val()
        var url = document.getElementById('add_hour_url').value

        console.log(day, from_hour, to_hour, is_offline, csrf_token)

        if(is_offline){
            is_offline = 'True'
            condition = "day != ''"
        }else{
            is_offline = 'False'
            condition = "day != '' && from_hour != '' && to_hour != ''"
        }

        if(eval(condition)){
            $.ajax({
                type: 'POST',
                url: url,
                data: {
                    'day': day,
                    'from_hour': from_hour,
                    'to_hour': to_hour,
                    'is_offline': is_offline,
                    'csrfmiddlewaretoken': csrf_token,
                },
                success: function(response){
                    if(response.status == 'success'){
                        if(response.is_offline == 'Offline'){
                            html ='<tr id="hour-'+response.id+'"><td><a href="#" class="font-weight-bold">{{ forloop.counter }}</a></td><td><span class="font-weight-normal">'+response.day+'</span></td><td><span class="font-weight-normal">Offline</span></td><td><a href="#" class="remove_hour" data-url="/doctor/opening-hours/remove/'+response.id+'/"><i class="fa fa-trash text-danger" aria-hidden="true"></i></a></td></tr>';
                        }else{
                            html ='<tr id="hour-'+response.id+'"><td><span class="font-weight-normal">'+response.day+'</span></td><td><span class="font-weight-normal">'+response.from_hour+' - '+response.to_hour+'</span></td><td><a href="#" class="remove_hour" data-url="/doctor/opening-hours/remove/'+response.id+'/"><i class="fa fa-trash text-danger" aria-hidden="true"></i></a></td></tr>';
                        }
                        
                        $(".opening_hours").append(html)
                        document.getElementById("opening_hours").reset();
                    }else{
                        swal(response.message, '', "error")
                    }
                }
            })
        }else{
            swal('Please fill all fields', '', 'info')
        }
    });

    // REMOVE OPENING HOUR
    $(document).on('click', '.remove_hour', function(e){
        e.preventDefault();
        url = $(this).attr('data-url');
        
        $.ajax({
            type: 'GET',
            url: url,
            success: function(response){
                if(response.status == 'success'){
                    document.getElementById('hour-'+response.id).remove()
                }
            }
        })
    })

   // document ready close 
});



// Dependent Dropdown logic


// function getCookie(name) {
//     let cookieValue = null;
//     if (document.cookie && document.cookie !== '') {
//         const cookies = document.cookie.split(';');
//         for (let i = 0; i < cookies.length; i++) {
//             const cookie = cookies[i].trim();
//             // Does this cookie string begin with the name we want?
//             if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                 cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                 break;
//             }
//         }
//     }
//     return cookieValue;
// }
// const csrftoken = getCookie('csrftoken');




// let animal_category_field = document.getElementById("id_animal_category")
// let animal_field = document.getElementById("id_animal")

// animal_category_field.addEventListener("change", pickState)
// function pickState(e){
//     animal_category_id = e.target.value
//     console.log(animal_category_id)
//     const data = { user_id: animal_category_id}
//     let url = "{% url 'getanimals' %}"

// fetch(url, {
// method: 'POST', // or 'PUT'
// headers: {
// 'Content-Type': 'application/json',
// 'X-CSRFToken': csrftoken
// },
// body: JSON.stringify(data),
// })
// .then(response => response.json())
// .then(data => {
// console.log('Success:', data[0]['animal_category']);

// animal_field.innerHTML = '<option value = "" selected="">----</option>'
// for(let i = 0; i<data.length; i++){ 
// animal_field.innerHTML += `<option value = "${data[i]["id"]}" selected="">${data[i]["name"]}</option>`

// }
// })
// .catch((error) => {
// console.error('Error:', error);
// });

// }