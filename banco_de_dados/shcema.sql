-- Active: 1788283799833@@127.0.0.1@5432@ecommerce
CREATE TABLE login (
    id serial PRIMARY KEY,
    nome varchar(100) NOT NULL,
    sobrenome varchar(100) NOT NULL,
    email varchar(100) UNIQUE NOT NULL,
    senha varchar(20) NOT NULL
)

CREATE TABLE produtos (
    id serial PRIMARY KEY,
    nome varchar(100) NOT NULL,
    descricao text NOT NULL,
    valor decimal(10, 2) NOT NULL,
    quantidade int NOT NULL
)

CREATE TABLE produto (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(100),
    valor DECIMAL(10, 2)
);

CREATE TABLE Pedidos (
    id SERIAL PRIMARY KEY,
    login_id INTEGER,
    total DECIMAL(10, 2),
    data TIMESTAMP,
    status VARCHAR(255),
    FOREIGN KEY (login_id) REFERENCES Login(id)
);

CREATE TABLE Carrinho (
    id SERIAL PRIMARY KEY,
    produtos_id INTEGER,
    pedido_id INTEGER,
    quantidade INTEGER,
    FOREIGN KEY (produtos_id) REFERENCES produto(id),
    FOREIGN KEY (pedido_id) REFERENCES Pedidos(id)
);

CREATE TABLE Pagamento (
    id SERIAL PRIMARY KEY,
    login_id INTEGER,
    pedido_id INTEGER,
    metodo VARCHAR(50),
    valor DECIMAL(10, 2),
    status VARCHAR(50),
    data TIMESTAMP,
    FOREIGN KEY (login_id) REFERENCES Login(id),
    FOREIGN KEY (pedido_id) REFERENCES Pedidos(id)
);