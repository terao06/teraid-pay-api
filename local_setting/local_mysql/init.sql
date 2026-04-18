SET NAMES utf8mb4;

-- ユーザーの認証プラグインを設定
ALTER USER 'teraid_pay_admin_user'@'%' IDENTIFIED BY 'password';
FLUSH PRIVILEGES;
CREATE DATABASE IF NOT EXISTS db_local;
