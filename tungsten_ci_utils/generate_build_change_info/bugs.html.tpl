<html>
<head>
<title>Bugs addressed between builds #{{ build_number_prev }} and #{{ build_number }}</title>
<style>
table { border-collapse: collapse;}
td, th { border: 1px solid black; padding: 10px }
</style>
</head>
<h1>Bugs addressed between builds #{{ build_number_prev }} and #{{ build_number }}</h1>
<table>
    <tr><th>Bug ID</th><th>Title</th><th>Changes</th></tr>
    {% for bug_id, bug  in bugs %}
    <tr>
        <td><b><a href="{{ bug.url | default("") }}">{{ bug_id }}</a></b></td>
        <td>{{ bug.title }}</td>
        <td>
        {% for change in bug.changes %}
        <a href="{{ change.commit.change.url | default("") }}">{{ change.commit.change.number | default("") }}</a>: {{ change.resolution }}<br>
        {% endfor %}
        </td>
    </tr>
    {% endfor %}
</table>
</html>
