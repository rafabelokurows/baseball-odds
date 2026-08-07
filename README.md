# Scraping sports (NFL and MLB) odds from sportsbook

Update 2024-12-05: It was good while it lasted. Betclic has changed their API, so I'm not able to scrape their odds (at least for the moment).
I've started an exploration.py script to see if I could get around their new validations. Let's see how that evolves.
New Security Validations: Cloudfront

## Alternative: Lumify API (working)

Betclic is blocked; [`scrape-lumify-games.py`](./scrape-lumify-games.py) pulls **MLB + NFL** schedules and moneylines/spreads/totals from [Lumify](https://lumify.ai) instead. Snapshots land in `data/lumify/`. Lumify also exposes **line-movement history** (`/v1/events/{id}/odds/history`) which maps cleanly to the short-term “odds move over time” goal.

```bash
# Free instant key (no signup): https://lumify.ai/docs/ai
export LUMIFY_API_KEY=lmfy-...
pip install -r requirements.txt
python scrape-lumify-games.py
```

GitHub Actions: workflow **“Scrape MLB/NFL odds via Lumify”** (`workflow_dispatch`). Add repo secret `LUMIFY_API_KEY`.

Update 2024-09-08: I renamed the repository as I've just added a scraper for NFL game odds to go with the one for MLB games that was already in place. 

**Short-term Goal**: analyzing how the moneyline and odds move over time for a certain game  

**Long-term Goal**: seeing if we could make f*cking money with this 🤑

Using Python and Github Actions for now

- [x] Add fallback for when API call returns no rows
- [x] Lumify API source for MLB/NFL odds (Betclic alternative)
- [ ] Start analyzing results to see trends on odds for one side or another

# Next steps
* Carregar todos os arquivos com as odds
* Agrupar por dia e jogo
* Ver odd final e odd inicial
* Obter dados para os jogos pós 09/05
  
Calcular:
* odds médias vencedor
* odds médias favoritos
* margem média de vitória
  * total
  * favorito
  * dark horse
  * away
  * home
* diferença média entre favorito e underdog

Estratégias:
 * home_team
 * favorito
 * away_team
 * underdog
 * best_record
 * triplas
 * duplas
formas diferentes de agrupar duplas/triplas

Value bets:
favoritos grande margem com odd 1.8+
