-- Crear usuario de replicación
CREATE USER IF NOT EXISTS 'replication_user'@'%' IDENTIFIED WITH mysql_native_password BY 'replication_password';
GRANT REPLICATION SLAVE ON *.* TO 'replication_user'@'%';
FLUSH PRIVILEGES;

-- Crear tablas necesarias para el sistema
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    profile_pic TEXT,
    birthdate DATE,
    city VARCHAR(255),
    personality VARCHAR(255),
    university VARCHAR(255),
    degree VARCHAR(255),
    gender VARCHAR(50),
    notifications BOOLEAN,
    accept_policies BOOLEAN,
    acceptance_date DATETIME,
    acceptance_ip VARCHAR(45),
    allow_anonimized_usage BOOLEAN
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transcriptions (
    transcription_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    transcription_date DATE,
    transcription_time TIME,
    text TEXT,
    emotion VARCHAR(50),
    sentiment VARCHAR(50),
    topic VARCHAR(255),
    emotion_probs_joy FLOAT,
    emotion_probs_anger FLOAT,
    emotion_probs_sadness FLOAT,
    emotion_probs_disgust FLOAT,
    emotion_probs_fear FLOAT,
    emotion_probs_neutral FLOAT,
    emotion_probs_surprise FLOAT,
    emotion_probs_trust FLOAT,
    emotion_probs_anticipation FLOAT,
    sentiment_probs_positive FLOAT,
    sentiment_probs_negative FLOAT,
    sentiment_probs_neutral FLOAT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;
