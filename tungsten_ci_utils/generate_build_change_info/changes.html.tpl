<html>
<head>
<style>
table { border-collapse: collapse;}
td, th { border: 1px solid black; padding: 10px }
</style>
</head>
<h1>Differences between builds #{{ build_number_prev }} and #{{ build_number }}</h1>
{% for canonical_name, project  in projects.items()  %}
<table>
<tr>
    <td><b>{{ project.name }}</b></td>
    {% if project.revisions.previous == project.revisions.current %}
    <td colspan=2>No changes ({{project.revisions.current}})</td>
    </tr>
    {% else %}
    <td>Prev commit: {{ project.revisions.previous }}</td>
    <td colspan=2>Current commit: {{ project.revisions.current }}</td>
    </tr>
<tr><th>Commit ID</th><th>Title</th><th>Author</th><th>Review</th></tr>
{% for change in project.changes %}
<tr>
<td>{{ change.sha[:7] }}</td>
<td>{{ change.title }}</td>
<td>{{ change.author.email }}</td>
<td><a href="{{ change.change.url | default("") }}">{{ change.change.number | default("") }}</a></td>
</tr>
{% endfor %}
{% endif %}
</table>
<br>
{% endfor %}

</html>
