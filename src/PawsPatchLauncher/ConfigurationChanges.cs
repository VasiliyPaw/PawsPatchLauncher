namespace PawsPatchLauncher;

public sealed record ConfigurationChange(string Name,string Before,string After);
public static class ConfigurationChanges
{
 public static IReadOnlyList<string> Describe(UserSettings before,UserSettings after,bool ru)
 {
  var changes=Compare(before,after,ru);
  return changes.Count==0?[ru?"Конфигурации совпадают.":"Configurations match."]
   :changes.Select(c=>c.Name+": "+c.Before+" → "+c.After).ToArray();
 }
 public static IReadOnlyList<ConfigurationChange> Compare(UserSettings before,UserSettings after,bool ru)
 {
  var lines=new List<ConfigurationChange>();
  void Change(string name,string oldValue,string newValue){if(oldValue!=newValue)lines.Add(new(name,oldValue,newValue));}
  string Flag(bool value)=>ru?(value?"вкл.":"выкл."):(value?"on":"off");
  string Channel(string value)=>value=="beta"?(ru?"Бета":"Beta"):(ru?"Релиз":"Release");
  string Spawn(string value)=>value=="x2"?"×2":value=="x4"?"×4":"×1";
  Change(ru?"Канал":"Channel",Channel(before.Channel),Channel(after.Channel));
  Change(ru?"Частота отрядов":"Roaming frequency",Spawn(before.RoamingSpawnMode),Spawn(after.RoamingSpawnMode));
  Change(ru?"Враждебность независимых":"Independent hostility",Flag(before.IndependentHostility),Flag(after.IndependentHostility));
  Change(ru?"Дополнительные отряды":"Additional roaming",Flag(before.AdditionalRoamingCompanies),Flag(after.AdditionalRoamingCompanies));
  Change(ru?"Баланс осады":"Siege balance",Flag(before.SiegeBalance),Flag(after.SiegeBalance));
  Change(ru?"Большие карты":"Large maps",Flag(before.LargeMapSizes),Flag(after.LargeMapSizes));
  Change(ru?"Русская локализация":"Russian localization",Flag(before.RussianLocalization),Flag(after.RussianLocalization));
  Change(ru?"Цвета игроков":"Player colors",Flag(before.CustomPlayerColors),Flag(after.CustomPlayerColors));
  Change(ru?"Пропуск рассинхронизации":"Continue after desync",Flag(before.DesyncMode=="continue"),Flag(after.DesyncMode=="continue"));
  Change(ru?"Отключение способностей и осколков":"Disable powers and shards",Flag(before.DisablePowersAndShards),Flag(after.DisablePowersAndShards));
  return lines;
 }
}
