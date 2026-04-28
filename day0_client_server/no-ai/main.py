import requests

def main():
    api_url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    response=requests.get(api_url)
    data=response.json()
    games=data["events"]
    
    for game in games:
        competitions=game["competitions"]

        

        for competition in competitions:
            competitors=competition["competitors"]
            home=competitors[0]if competitors[0]["homeAway"].lower()=="home" else competitors[1]
            away=competitors[0]if competitors[0]["homeAway"].lower()=="away" else competitors[1]
            if(not game["status"]["type"]["completed"]):
                print(f"{away["team"]["displayName"]} vs {home["team"]["displayName"]} (scheduled)")
                
            else:
                print(f"{away["team"]["displayName"]} {away["score"]} - {home["team"]["displayName"]} {home["score"]}")

      
            

if __name__== "__main__":
    main()