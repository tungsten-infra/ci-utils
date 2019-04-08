<html>
<head>
<style>
table { border-collapse: collapse;}
td, th { border: 1px solid black; padding: 10px }
</style>
</head>
<h1>Differences between builds #{{ build_number_prev }} and #{{ build_number }}</h1>
{% if fetched_prev %}
<h5>Build #{{ build_number_prev }} was automatically detected as the last previous successful nightly build before #{{ build_number }}
{% endif %}
{% for canonical_name, project  in projects.items()  %}
<table>
<tr>
    <td><b>{{ project.name }}</b></td>
    {% if not project.changes %}
    <td colspan=2>No changes ({{ project.revisions.current }})</td>
    </tr>
    {% else %}
    <td>Prev commit: {{ "Unknown" if project.revisions.previous is none else project.revisions.previous }}</td>
    <td colspan=3>Current commit: {{ "Unknown" if project.revisions.current is none else project.revisions.current }}</td>
    </tr>
<tr><th>Commit ID</th><th>Title</th><th>Author</th><th>Review</th><th>Bugs</th</tr>
{% for change in project.changes %}
<tr>
<td>{{ change.sha[:7] }}</td>
<td>{{ change.title }}</td>
<td>{{ change.author.email }}</td>
<td><a href="{{ change.change.url | default("") }}">{{ change.change.number | default("") }}</a></td>
<td>
{% for bug in change.bugs %}
<a href="{{ bug.url | default("") }}">{{ bug.resolution }}: {{bug.id }}</a><br>
{% endfor %}
</td>
</tr>
{% endfor %}
{% endif %}
</table>
<br>
{% endfor %}

</html>
