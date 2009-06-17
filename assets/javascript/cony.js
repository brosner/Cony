var queues = new Object;
queues.memory = [];
queues.messages = [];
queues.transactions = [];
queues.consumers = [];

var interval = 1000;
var max_datapoints = 300;

function getListQueueData()
{
  $.ajax({
    type: "GET",
    url: "/jsonpStats/list_queues",
    dataType: "script"
  });  
}

function cony_init()
{
  $('#tabs').tabs();
  $.ajax({
    type: "GET",
    url: "/config",
    dataType: "script"
  });
  getListQueueData();
  $('#intervalAmount').html(interval / 1000);
}

function number_format( number, decimals, dec_point, thousands_sep ) {
    // http://kevin.vanzonneveld.net
    // +   original by: Jonas Raoni Soares Silva (http://www.jsfromhell.com)
    // +   improved by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
    // +     bugfix by: Michael White (http://getsprink.com)
    // +     bugfix by: Benjamin Lupton
    // +     bugfix by: Allan Jensen (http://www.winternet.no)
    // +    revised by: Jonas Raoni Soares Silva (http://www.jsfromhell.com)
    // +     bugfix by: Howard Yeend
    // +    revised by: Luke Smith (http://lucassmith.name)
    // +     bugfix by: Diogo Resende
    // +     bugfix by: Rival
    // +     input by: Kheang Hok Chin (http://www.distantia.ca/)
    // +     improved by: davook
    // +     improved by: Brett Zamir (http://brett-zamir.me)
    // *     example 1: number_format(1234.56);
    // *     returns 1: '1,235'
    // *     example 2: number_format(1234.56, 2, ',', ' ');
    // *     returns 2: '1 234,56'
    // *     example 3: number_format(1234.5678, 2, '.', '');
    // *     returns 3: '1234.57'
    // *     example 4: number_format(67, 2, ',', '.');
    // *     returns 4: '67,00'
    // *     example 5: number_format(1000);
    // *     returns 5: '1,000'
    // *     example 6: number_format(67.311, 2);
    // *     returns 6: '67.31'
    // *     example 7: number_format(1000.55, 1);
    // *     returns 7: '1,000.6'
    // *     example 8: number_format(67000, 5, ',', '.');
    // *     returns 8: '67.000,00000'
    // *     example 9: number_format(0.9, 0);
    // *     returns 9: '1'
    var n = number, prec = decimals;
    var toFixedFix = function (n,prec) {
        var k = Math.pow(10,prec);
        return (Math.round(n*k)/k).toString();
    };
 
    n = !isFinite(+n) ? 0 : +n;
    prec = !isFinite(+prec) ? 0 : Math.abs(prec);
    var sep = (typeof thousands_sep === 'undefined') ? ',' : thousands_sep;
    var dec = (typeof dec_point === 'undefined') ? '.' : dec_point;
 
    var s = (prec > 0) ? toFixedFix(n, prec) : toFixedFix(Math.round(n), prec); //fix for IE parseFloat(0.55).toFixed(0) = 0;
 
    var abs = toFixedFix(Math.abs(n), prec);
    var _, i;
 
    if (abs >= 1000) {
        _ = abs.split(/\D/);
        i = _[0].length % 3 || 3;
 
        _[0] = s.slice(0,i + (n < 0)) +
              _[0].slice(i).replace(/(\d{3})/g, sep+'$1');
        s = _.join(dec);
    } else {
        s = s.replace('.', dec);
    }
    if (s.indexOf(dec) === -1 && prec > 1) {
        s += dec+new Array(prec).join(0)+'0';
    }
    return s;
}

function getPrettySize(value)
{
  if ( value < 1024 )
  {
    return value + ' Bytes';
  }
  if ( value < 1048576 )
  {
    return number_format( value / 1024, 2, '.', ','  ) + ' KB';
  }
  if ( value < 1073741824 )
  {
    return number_format( value / 1048576, 2, '.', ','  ) + ' MB';
  }
  if ( value < 1099511627776 )
  {
    return number_format( value / 1073741824, 2, '.', ','  ) + ' GB';
  }
}


function getTime()
{
  var currentTime = new Date();
  return currentTime.getTime();
}

function getPrintableTime()
{
  var currentTime = new Date();
  var hours = currentTime.getHours();
  var minutes = currentTime.getMinutes();
  var seconds = currentTime.getSeconds();
  if (minutes < 10){
    minutes = "0" + minutes;
  }
  if (seconds < 10){
    seconds = "0" + seconds;
  }
  return hours + ":" + minutes + ":" + seconds;
}

function jsonpConfig(data)
{
  var title = 'Cony :: ' + data.RabbitMQ.RabbitNode + ' :: Real-time RabbitMQ Monitor';
  $('h1#title').html(title);
  document.title = title;
}

function listQueues(data)
{
  var totalMemory = 0;
  
  $.each(data, function(name, attributes){

    // Consumers
    index = -1;
    l = queues.consumers.length;
    for ( var y = 0; y < l; y++ )
    {
      if ( queues.consumers[y].label == name )
      {
        index = y;
        break;
      }
    }
    if ( index === -1 )
    {
      index = l;
      queues.consumers[index] = new Object;
      queues.consumers[index] = {label: name, data: 0};
    }
    queues.consumers[index].data = attributes.consumers;
  
    // Memory
    index = -1;
    l = queues.memory.length;
    for ( var y = 0; y < l; y++ )
    {
      if ( queues.memory[y].label == name )
      {
        index = y;
        break;
      }
    }
    if ( index === -1 )
    {
      index = l;
      queues.memory[index] = new Object;
      queues.memory[index] = {label: name, data: []};
    }
    queues.memory[index].data.push([getTime(), attributes.memory]);
    if ( queues.memory[index].data.length > max_datapoints )
    {
      queues.memory[index].data.shift();
    }   
    totalMemory += attributes.memory;
    
    // Messages
    index = -1;
    l = queues.messages.length;
    for ( y = 0; y < l; y++ )
    {
      if ( queues.messages[y].label == name )
      {
        index = y;
        break;
      }
    }
    if ( index === -1 )
    {
      index = l;
      queues.messages[index] = new Object;
      queues.messages[index] = {label: name, data: []};
    }
    queues.messages[index].data.push([getTime(), attributes.messages]);
    if ( queues.messages[index].data.length > max_datapoints )
    {
      queues.messages[index].data.shift();
    }   

    // Transactions
    index = -1;
    l = queues.transactions.length;
    for ( y = 0; y < l; y++ )
    {
      if ( queues.transactions[y].label == name )
      {
        index = y;
        break;
      }
    }
    if ( index === -1 )
    {
      index = l;
      queues.transactions[index] = new Object;
      queues.transactions[index] = {label: name, data: []};
    }
    queues.transactions[index].data.push([getTime(), attributes.transactions]);
    if ( queues.transactions[index].data.length > max_datapoints )
    {
      queues.transactions[index].data.shift();
    }   
    
  });
 
  // Consumers 
  var html = '';
  var totalCount = 0;
  for ( var y = 0; y < queues.consumers.length; y++ )
  {
    html += '<dt>' + queues.consumers[y].label + '</dt><dd>' + queues.consumers[y].data + '</dd>';
    totalCount += queues.consumers[y].data;
  }
  html += '<dt class="total">Total Consumers</dt><dd class="total">' +  number_format(totalCount, 0, '.', ',') + '</dd>';
  $('#consumerList').html(html);

  // Queue Depths
  html = '';
  totalCount = 0;
  for ( var y = 0; y < queues.messages.length; y++ )
  {
    index = queues.messages[y].data.length - 1;
    count = queues.messages[y].data[index][1];
    totalCount += count;
    html += '<dt>' + queues.messages[y].label + '</dt><dd>' + number_format(count, 0, '.', ',')  + '</dd>';
  }
  html += '<dt class="total">Total Messages</dt><dd class="total">' +  number_format(totalCount, 0, '.', ',') + '</dd>';
  $('#queueDepthList').html(html);
  
  // Memory
  html = '';
  for ( var y = 0; y < queues.memory.length; y++ )
  {
    index = queues.memory[y].data.length - 1;
    count = queues.memory[y].data[index][1];
    html += '<dt>' + queues.memory[y].label + '</dt><dd>' + getPrettySize(count)  + '</dd>';
  }
  html += '<dt class="total">Total Memory Usage</dt><dd class="total">' + getPrettySize(totalMemory) + '</dd>';
  $('#memoryStats').html(html);  
  
  $.plot($('#queueMemoryUsage'), queues.memory,
        { borderWidth: '1px', xaxis: {mode: "time"}, yaxis: {label: 'Bytes'},
        legend: { position: "ne", borderWidth: '1px' } } 
  );

  $.plot($('#queueDepths'), queues.messages,
        { borderWidth: '1px', xaxis: {mode: "time"}, yaxis: {label: 'Bytes'},
        legend: { position: "ne", borderWidth: '1px' } } 
  );

  $.plot($('#queueTransactions'), queues.transactions,
        { borderWidth: '1px', xaxis: {mode: "time"}, yaxis: {label: 'Bytes'},
        legend: { position: "ne", borderWidth: '1px' } } 
  );

  $('#lastUpdate').html(getPrintableTime());

  setTimeout(getListQueueData, interval);  
}