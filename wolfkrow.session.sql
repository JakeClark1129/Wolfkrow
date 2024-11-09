-- @block

CREATE TABLE Tasks(
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255),
    inputs JSON,
    outputs JSON
);

-- @block

INSERT INTO Tasks (name, inputs, outputs) VALUES ("name", '[{"foo": "bar"}, {"output": "out"}]', '[{"foo": "bar"}, {"output": "out"}]');


-- @block

SELECT * FROM Tasks;

