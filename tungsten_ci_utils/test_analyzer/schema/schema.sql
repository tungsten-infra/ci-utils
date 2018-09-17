CREATE TABLE testcase_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status INT NOT NULL,

    class_name VARCHAR(255),
    testsuite_name VARCHAR(255),
    testsuite_package VARCHAR(255),

    project VARCHAR(255) NOT NULL,
    project_commit VARCHAR(50),

    build_id VARCHAR(50) NOT NULL,
    execution_no INT

)
