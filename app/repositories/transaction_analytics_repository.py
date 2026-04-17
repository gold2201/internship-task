from sqlalchemy import text
from sqlalchemy.orm import Session


class TransactionAnalyticsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_full_analysis(self) -> list[dict]:
        """
        Сначала создаём таблицу с началом и концом каждых 52-ух недель.
        Далее считаем статистику пользователей:
        все пользователи за неделю, активные пользователи с депозитом и активные пользователи без откаченных транзакций.
        Соединяем с помощью LEFT JOIN user недели и пользователей созданных в этой неделе,
        а с помощью LEFT JOIN присоединяем к этим пользователям их транзакции.
        Далее статистика транзакций:
        сколько всего транзакций за неделю, сколько из них не откаченные,
        сумма всех положительных не откаченных сумм за неделю, сумма всех отрицательных не откаченных сумм за неделю.
        И к каждой неделе присоедини транзакции, созданные в эту неделю с помощью LEFT JOIN transaction
        Далее объединяем две таблицы (user_stats и tx_stats) по дате начала недели.
        """
        sql = text("""
            WITH weeks AS (
                SELECT
                    generate_series(
                        date_trunc('week', NOW()) - interval '51 weeks',
                        date_trunc('week', NOW()),
                        interval '1 week'
                    ) AS week_start,
                    
                    generate_series(
                        date_trunc('week', NOW()) - interval '51 weeks',
                        date_trunc('week', NOW()),
                        interval '1 week'
                    ) + interval '1 week' AS week_end
            ),
            user_stats AS (
                SELECT
                    w.week_start,
                    w.week_end,
                    
                    COUNT(u.id) FILTER (WHERE u.created >= w.week_start AND u.created < w.week_end) AS registered_users,
                    
                    COUNT(DISTINCT u.id) FILTER (
                        WHERE u.status = 'ACTIVE'
                        AND t.amount > 0
                        AND t.created >= w.week_start
                        AND t.created < w.week_end
                    ) AS deposit_users,
                    
                    COUNT(DISTINCT u.id) FILTER (
                        WHERE u.status = 'ACTIVE'
                        AND t.amount > 0
                        AND t.status != 'ROLLBACKED'
                        AND t.created >= w.week_start
                        AND t.created < w.week_end
                    ) AS not_rollbacked_deposit_users
                
                FROM weeks w
                LEFT JOIN "user" u ON u.created >= w.week_start AND u.created < w.week_end
                LEFT JOIN transaction t ON t.user_id = u.id
                GROUP BY w.week_start, w.week_end
            ),
            tx_stats AS (
                SELECT
                    w.week_start,
                    
                    COUNT(t.id) AS total_tx,
                    
                    COUNT(t.id) FILTER (WHERE t.status != 'ROLLBACKED') AS not_rollbacked_tx,
                    
                    COALESCE(SUM(t.amount) FILTER (
                        WHERE t.amount > 0 AND t.status != 'ROLLBACKED'
                        AND t.created >= w.week_start AND t.created < w.week_end
                    ), 0) AS deposit_amount,
                    
                    COALESCE(SUM(t.amount) FILTER (
                        WHERE t.amount < 0 AND t.status != 'ROLLBACKED'
                        AND t.created >= w.week_start AND t.created < w.week_end
                    ), 0) AS withdraw_amount
                
                FROM weeks w
                LEFT JOIN transaction t ON t.created >= w.week_start AND t.created < w.week_end
                GROUP BY w.week_start
            )
            SELECT
                u.week_start,
                u.week_end,
                u.registered_users,
                u.deposit_users,
                u.not_rollbacked_deposit_users,
                t.total_tx,
                t.not_rollbacked_tx,
                t.deposit_amount,
                t.withdraw_amount
            FROM user_stats u
            JOIN tx_stats t ON u.week_start = t.week_start
            ORDER BY u.week_start DESC
        """)
        return [row._asdict() for row in self.session.execute(sql).all()]
