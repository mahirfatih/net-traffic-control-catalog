# Dead-domain sweep

Generated: 2026-10-14

Two rounds, at least ten minutes apart, asking Cloudflare and Google
directly about A, AAAA and NS. A host is only *dead* when every one of
the six questions in **both** rounds answers NXDOMAIN.

| Round | alive | nodata | servfail | dead | unknown |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 6418 | 37 | 266 | 435 | 21 |
| 2 | 6419 | 38 | 266 | 433 | 21 |

## Worth a look — 532 host(s) SERVFAIL from every resolver

Kept, not dropped. A zone that SERVFAILs everywhere is usually a name
whose registration lapsed, so its category may now describe whoever
holds it. This is the recycling risk; it is reported, not acted on.

- `abgs.gov.tr` (government)
- `abgs.gov.tr` (government)
- `activision.asia` (gaming)
- `activision.asia` (gaming)
- `activision.biz` (gaming)
- `activision.biz` (gaming)
- `activision.ca` (gaming)
- `activision.ca` (gaming)
- `activision.cn` (gaming)
- `activision.cn` (gaming)
- `activision.co.in` (gaming)
- `activision.co.in` (gaming)
- `activision.com.sg` (gaming)
- `activision.com.sg` (gaming)
- `activision.com.tw` (gaming)
- `activision.com.tw` (gaming)
- `activision.eu` (gaming)
- `activision.eu` (gaming)
- `activision.hk` (gaming)
- `activision.hk` (gaming)
- `activision.in` (gaming)
- `activision.in` (gaming)
- `activision.mobi` (gaming)
- `activision.mobi` (gaming)
- `activision.on.ca` (gaming)
- `activision.on.ca` (gaming)
- `activision.org.uk` (gaming)
- `activision.org.uk` (gaming)
- `activision.sg` (gaming)
- `activision.sg` (gaming)
- `activision.us` (gaming)
- `activision.us` (gaming)
- `activisionblizzard.at` (gaming)
- `activisionblizzard.at` (gaming)
- `activisionblizzard.br.com` (gaming)
- `activisionblizzard.br.com` (gaming)
- `activisionblizzard.cn.com` (gaming)
- `activisionblizzard.cn.com` (gaming)
- `activisionblizzard.gb.net` (gaming)
- `activisionblizzard.gb.net` (gaming)
- `activisionblizzard.jpn.com` (gaming)
- `activisionblizzard.jpn.com` (gaming)
- `activisionblizzard.net.nz` (gaming)
- `activisionblizzard.net.nz` (gaming)
- `activisionblizzard.sa.com` (gaming)
- `activisionblizzard.sa.com` (gaming)
- `activisionblizzard.se.net` (gaming)
- `activisionblizzard.se.net` (gaming)
- `activisionblizzard.tw` (gaming)
- `activisionblizzard.tw` (gaming)
- `activisionblizzard.uk.net` (gaming)
- `activisionblizzard.uk.net` (gaming)
- `activisionblizzard.za.com` (gaming)
- `activisionblizzard.za.com` (gaming)
- `adli-sicil.gov.tr` (government)
- `adli-sicil.gov.tr` (government)
- `afetacil.gov.tr` (government)
- `afetacil.gov.tr` (government)
- `ahis.gov.tr` (government)
- `ahis.gov.tr` (government)
- `alawwalbank.com` (finance)
- `alawwalbank.com` (finance)
- `atb.gov.tr` (government)
- `atb.gov.tr` (government)
- `avon.payupay.ru` (finance)
- `avon.payupay.ru` (finance)
- `bankrazvitie.ru` (finance)
- `bankrazvitie.ru` (finance)
- `basbakanlik-dpb.gov.tr` (government)
- `basbakanlik-dpb.gov.tr` (government)
- `bidv.com` (finance)
- `bidv.com` (finance)
- `bing.cn` (search)
- `bing.cn` (search)
- `blizzard.asia` (gaming)
- `blizzard.asia` (gaming)
- `blizzard.co` (gaming)
- `blizzard.co` (gaming)
- `blizzard.com.au` (gaming)
- `blizzard.com.au` (gaming)
- `blizzard.game` (gaming)
- `blizzard.game` (gaming)
- `blizzard.games` (gaming)
- `blizzard.games` (gaming)
- `blizzard.info` (gaming)
- `blizzard.info` (gaming)
- `blizzard.mobi` (gaming)
- `blizzard.mobi` (gaming)
- `blizzard.sg` (gaming)
- `blizzard.sg` (gaming)
- `blizzard.tv` (gaming)
- `blizzard.tv` (gaming)
- `blizzardactivision.at` (gaming)
- `blizzardactivision.at` (gaming)
- `blizzardactivision.br.com` (gaming)
- `blizzardactivision.br.com` (gaming)
- `blizzardactivision.cn.com` (gaming)
- `blizzardactivision.cn.com` (gaming)
- `blizzardactivision.gb.net` (gaming)
- `blizzardactivision.gb.net` (gaming)
- `blizzardactivision.jpn.com` (gaming)
- `blizzardactivision.jpn.com` (gaming)
- `blizzardactivision.sa.com` (gaming)
- `blizzardactivision.sa.com` (gaming)
- `blizzardactivision.se.net` (gaming)
- `blizzardactivision.se.net` (gaming)
- `blizzardactivision.tw` (gaming)
- `blizzardactivision.tw` (gaming)
- `blizzardactivision.uk.net` (gaming)
- `blizzardactivision.uk.net` (gaming)
- `blizzardactivision.za.com` (gaming)
- `blizzardactivision.za.com` (gaming)
- `btc-e.com` (finance)
- `btc-e.com` (finance)
- `bumko.gov.tr` (government)
- `bumko.gov.tr` (government)
- `calisma.gov.tr` (government)
- `calisma.gov.tr` (government)
- `callofduty.asia` (gaming)
- `callofduty.asia` (gaming)
- `callofduty.mobi` (gaming)
- `callofduty.mobi` (gaming)
- `callofduty.org` (gaming)
- `callofduty.org` (gaming)
- `cankaya.gov.tr` (government)
- `cdn.vidible.tv` (video)
- `cdn.vidible.tv` (video)
- `clb.bankmtb.ru` (finance)
- `clb.bankmtb.ru` (finance)
- `client.nb-bank.ru` (finance)
- `client.nb-bank.ru` (finance)
- `client.rfabank.ru` (finance)
- `client.rfabank.ru` (finance)
- `client.vpb.ru` (finance)
- `client.vpb.ru` (finance)
- `cmbank.ru` (finance)
- `cmbank.ru` (finance)
- `dbo.assotsiatsiyabank.ru` (finance)
- `dbo.assotsiatsiyabank.ru` (finance)
- `delivery.vidible.tv` (video)
- `delivery.vidible.tv` (video)
- `deprem.gov.tr` (government)
- `deprem.gov.tr` (government)
- `dhmiata.gov.tr` (government)
- `dhmiata.gov.tr` (government)
- `diablo.app` (gaming)
- `diablo.app` (gaming)
- `diablo.asia` (gaming)
- `diablo.asia` (gaming)
- `diablo.com.au` (gaming)
- `diablo.com.au` (gaming)
- `diablo.com.tw` (gaming)
- `diablo.com.tw` (gaming)
- `diablo.game` (gaming)
- `diablo.game` (gaming)
- `diablo.games` (gaming)
- `diablo.games` (gaming)
- `diablo.ne.kr` (gaming)
- `diablo.ne.kr` (gaming)
- `diablo.net.au` (gaming)
- `diablo.net.au` (gaming)
- `diablo.net.cn` (gaming)
- `diablo.net.cn` (gaming)
- `diablo.sg` (gaming)
- `diablo.sg` (gaming)
- `diablo.tw` (gaming)
- `diablo.tw` (gaming)
- `dpb.gov.tr` (government)
- `dpb.gov.tr` (government)
- `e-pay.by` (finance)
- `e-pay.by` (finance)
- `foreigntrade.gov.tr` (government)
- `garplinyitleri.gov.tr` (government)
- `garplinyitleri.gov.tr` (government)
- `gata.edu.tr` (education)
- `gata.edu.tr` (education)
- `geometrywars.com` (gaming)
- `geometrywars.com` (gaming)
- `github.education` (software)
- `github.education` (software)
- `github.engineering` (software)
- `github.engineering` (software)
- `github.enterprises` (software)
- `github.enterprises` (software)
- `github.exchange` (software)
- `github.exchange` (software)
- `github.expert` (software)
- `github.expert` (software)
- `github.exposed` (software)
- `github.exposed` (software)
- `github.express` (software)
- `github.express` (software)
- `github.fail` (software)
- `github.fail` (software)
- `github.family` (software)
- `github.family` (software)
- `github.foundation` (software)
- `github.foundation` (software)
- `github.gallery` (software)
- `github.gallery` (software)
- `github.gq` (software)
- `github.gq` (software)
- `github.hosting` (software)
- `github.hosting` (software)
- `github.industries` (software)
- `github.industries` (software)
- `github.institute` (software)
- `github.institute` (software)
- `github.legal` (software)
- `github.legal` (software)
- `github.lgbt` (software)
- `github.lgbt` (software)
- `github.limited` (software)
- `github.limited` (software)
- `github.live` (software)
- `github.live` (software)
- `github.marketing` (software)
- `github.marketing` (software)
- `github.markets` (software)
- `github.markets` (software)
- `github.ml` (software)
- `github.ml` (software)
- `github.movie` (software)
- `github.movie` (software)
- `github.parts` (software)
- `github.parts` (software)
- `github.photo` (software)
- `github.photo` (software)
- `github.photos` (software)
- `github.photos` (software)
- `github.pics` (software)
- `github.pics` (software)
- `github.pictures` (software)
- `github.pictures` (software)
- `github.pink` (software)
- `github.pink` (software)
- `github.place` (software)
- `github.place` (software)
- `github.plus` (software)
- `github.plus` (software)
- `github.porn` (software)
- `github.porn` (software)
- `github.press` (software)
- `github.press` (software)
- `github.pro` (software)
- `github.pro` (software)
- `github.productions` (software)
- `github.productions` (software)
- `github.properties` (software)
- `github.properties` (software)
- `github.property` (software)
- `github.property` (software)
- `github.report` (software)
- `github.report` (software)
- `github.rest` (software)
- `github.rest` (software)
- `github.rip` (software)
- `github.rip` (software)
- `github.school` (software)
- `github.school` (software)
- `github.sex` (software)
- `github.sex` (software)
- `github.show` (software)
- `github.show` (software)
- `github.software` (software)
- `github.software` (software)
- `github.solutions` (software)
- `github.solutions` (software)
- `github.studio` (software)
- `github.studio` (software)
- `github.study` (software)
- `github.study` (software)
- `github.style` (software)
- `github.style` (software)
- `github.sucks` (software)
- `github.sucks` (software)
- `github.supplies` (software)
- `github.supplies` (software)
- `github.supply` (software)
- `github.supply` (software)
- `github.systems` (software)
- `github.systems` (software)
- `github.technology` (software)
- `github.technology` (software)
- `github.tokyo` (software)
- `github.tokyo` (software)
- `github.tools` (software)
- `github.tools` (software)
- `github.tours` (software)
- `github.tours` (software)
- `github.training` (software)
- `github.training` (software)
- `github.university` (software)
- `github.university` (software)
- `github.ventures` (software)
- `github.ventures` (software)
- `github.video` (software)
- `github.video` (software)
- `github.vision` (software)
- `github.vision` (software)
- `github.vote` (software)
- `github.vote` (software)
- `github.voyage` (software)
- `github.voyage` (software)
- `github.watch` (software)
- `github.watch` (software)
- `github.world` (software)
- `github.world` (software)
- `githubcloud.biz` (software)
- `githubcloud.biz` (software)
- `githubcloud.co` (software)
- `githubcloud.co` (software)
- `githubcloud.cz` (software)
- `githubcloud.cz` (software)
- `githubcloud.info` (software)
- `githubcloud.info` (software)
- `githubcloud.jp` (software)
- `githubcloud.jp` (software)
- `githubcloud.me` (software)
- `githubcloud.me` (software)
- `githubcloud.mobi` (software)
- `githubcloud.mobi` (software)
- `githubcloud.net` (software)
- `githubcloud.net` (software)
- `githubcloud.org` (software)
- `githubcloud.org` (software)
- `githubcloud.tv` (software)
- `githubcloud.tv` (software)
- `githubcloud.us` (software)
- `githubcloud.us` (software)
- `globexbank.ru` (finance)
- `globexbank.ru` (finance)
- `gumruk.gov.tr` (government)
- `gumruk.gov.tr` (government)
- `gws.sauberbank.com` (finance)
- `gws.sauberbank.com` (finance)
- `hb.unionbank.co.il` (finance)
- `hb.unionbank.co.il` (finance)
- `highmoon.net` (gaming)
- `highmoon.net` (gaming)
- `hockeyapp.net` (crash)
- `hockeyapp.net` (crash)
- `hu.edu.tr` (education)
- `hubot.app` (software)
- `hubot.app` (software)
- `hubot.club` (software)
- `hubot.club` (software)
- `hubot.co` (software)
- `hubot.co` (software)
- `hubot.dev` (software)
- `hubot.dev` (software)
- `hubot.global` (software)
- `hubot.global` (software)
- `hubot.jp` (software)
- `hubot.jp` (software)
- `ib.banknp.ru` (finance)
- `ib.banknp.ru` (finance)
- `ib.solidar.ru` (finance)
- `ib.solidar.ru` (finance)
- `ib.svabank.ru` (finance)
- `ib.svabank.ru` (finance)
- `ibank.akcia-bank.ru` (finance)
- `ibank.akcia-bank.ru` (finance)
- `ibank.informpb.ru` (finance)
- `ibank.informpb.ru` (finance)
- `ibank.sistemabank.ru` (finance)
- `ibank.sistemabank.ru` (finance)
- `ibank2.vpb.su` (finance)
- `ibank2.vpb.su` (finance)
- `iegm.gov.tr` (government)
- `iegm.gov.tr` (government)
- `iem.gov.tr` (government)
- `iem.gov.tr` (government)
- `ifobs.bankcenter.com.ua` (finance)
- `ifobs.bankcenter.com.ua` (finance)
- `infinityward.net` (gaming)
- `infinityward.net` (gaming)
- `ioffice.kz` (finance)
- `ioffice.kz` (finance)
- `karakoyunlu.bel.tr` (government)
- `kbi.gov.tr` (government)
- `kbi.gov.tr` (government)
- `khgm.gov.tr` (government)
- `khgm.gov.tr` (government)
- `kou.edu.tr` (education)
- `kou.edu.tr` (education)
- `kssgm.gov.tr` (government)
- `kssgm.gov.tr` (government)
- `lk.bcsb.ru` (finance)
- `lk.bcsb.ru` (finance)
- `mahalli-idareler.gov.tr` (government)
- `mahalli-idareler.gov.tr` (government)
- `maliye.gov.tr` (government)
- `maliye.gov.tr` (government)
- `manifest.auditude.com` (encyclopedia)
- `manifest.auditude.com` (encyclopedia)
- `mbank.kiev.ua` (finance)
- `mbank.kiev.ua` (finance)
- `meteor.gov.tr` (government)
- `meteor.gov.tr` (government)
- `my.pervobank.ru` (finance)
- `my.pervobank.ru` (finance)
- `myaltyn.kz` (finance)
- `myaltyn.kz` (finance)
- `netdna-cdn.com` (cdn)
- `netdna-cdn.com` (cdn)
- `nordea.ru` (finance)
- `nordea.ru` (finance)
- `npmjs.ai` (software)
- `npmjs.ai` (software)
- `npmjs.host` (software)
- `npmjs.host` (software)
- `npmjs.link` (software)
- `npmjs.link` (software)
- `octodns.com` (software)
- `octodns.com` (software)
- `octokit.org` (software)
- `octokit.org` (software)
- `officelabs-int.com` (software)
- `officelabs-int.com` (software)
- `online-banking.hsbc.com.ar` (finance)
- `online-banking.hsbc.com.ar` (finance)
- `oskolbank.ru` (finance)
- `oskolbank.ru` (finance)
- `otpdirekt.ro` (finance)
- `otpdirekt.ro` (finance)
- `pay.platimo.ua` (finance)
- `pay.platimo.ua` (finance)
- `pitfall.mobi` (gaming)
- `pitfall.mobi` (gaming)
- `pkb24.ru` (finance)
- `pkb24.ru` (finance)
- `probot.app` (software)
- `probot.app` (software)
- `ravensoftware.info` (gaming)
- `ravensoftware.info` (gaming)
- `ravensoftware.net` (gaming)
- `ravensoftware.net` (gaming)
- `rbkmoney.ru` (finance)
- `rbkmoney.ru` (finance)
- `rigeb.gov.tr` (government)
- `rigeb.gov.tr` (government)
- `seninbankan.com.tr` (finance)
- `seninbankan.com.tr` (finance)
- `sgeb.bg` (finance)
- `sgeb.bg` (finance)
- `sierra.biz` (gaming)
- `sierra.biz` (gaming)
- `sierra.info` (gaming)
- `sierra.info` (gaming)
- `sierra.mobi` (gaming)
- `sierra.mobi` (gaming)
- `sierra.us` (gaming)
- `sierra.us` (gaming)
- `sparkasse-erwitte-anroechte.de` (finance)
- `sparkasse-erwitte-anroechte.de` (finance)
- `spyro.fr` (gaming)
- `spyro.fr` (gaming)
- `spyro.mobi` (gaming)
- `spyro.mobi` (gaming)
- `spyro.us` (gaming)
- `spyro.us` (gaming)
- `ssgm.gov.tr` (government)
- `ssgm.gov.tr` (government)
- `starcraft.app` (gaming)
- `starcraft.app` (gaming)
- `starcraft.asia` (gaming)
- `starcraft.asia` (gaming)
- `starcraft.com.au` (gaming)
- `starcraft.com.au` (gaming)
- `starcraft.com.tw` (gaming)
- `starcraft.com.tw` (gaming)
- `starcraft.fr` (gaming)
- `starcraft.fr` (gaming)
- `starcraft.game` (gaming)
- `starcraft.game` (gaming)
- `starcraft.games` (gaming)
- `starcraft.games` (gaming)
- `starcraft.mobi` (gaming)
- `starcraft.mobi` (gaming)
- `starcraft.sg` (gaming)
- `starcraft.sg` (gaming)
- `starcraft.tw` (gaming)
- `starcraft.tw` (gaming)
- `sulusaray60.bel.tr` (government)
- `sulusaray60.bel.tr` (government)
- `tagilbank.ru` (finance)
- `tagilbank.ru` (finance)
- `tdci.gov.tr` (government)
- `tdci.gov.tr` (government)
- `tekmer.gov.tr` (government)
- `tekmer.gov.tr` (government)
- `treasury.gov.tr` (government)
- `treasury.gov.tr` (government)
- `tugsas.gov.tr` (government)
- `tugsas.gov.tr` (government)
- `tyih.gov.tr` (government)
- `tyih.gov.tr` (government)
- `videos.vidible.tv` (video)
- `videos.vidible.tv` (video)
- `warcraft.app` (gaming)
- `warcraft.app` (gaming)
- `warcraft.com.au` (gaming)
- `warcraft.com.au` (gaming)
- `warcraft.com.tw` (gaming)
- `warcraft.com.tw` (gaming)
- `warcraft.game` (gaming)
- `warcraft.game` (gaming)
- `warcraft.games` (gaming)
- `warcraft.games` (gaming)
- `warcraft.mobi` (gaming)
- `warcraft.mobi` (gaming)
- `warcraft.tw` (gaming)
- `warcraft.tw` (gaming)
- `worldofwarcraft.app` (gaming)
- `worldofwarcraft.app` (gaming)
- `worldofwarcraft.asia` (gaming)
- `worldofwarcraft.asia` (gaming)
- `worldofwarcraft.com.mx` (gaming)
- `worldofwarcraft.com.mx` (gaming)
- `worldofwarcraft.game` (gaming)
- `worldofwarcraft.game` (gaming)
- `worldofwarcraft.games` (gaming)
- `worldofwarcraft.games` (gaming)
- `worldofwarcraft.kr` (gaming)
- `worldofwarcraft.kr` (gaming)
- `worldofwarcraft.ru` (gaming)
- `worldofwarcraft.ru` (gaming)
- `www2.jugra.ru` (finance)
- `www2.jugra.ru` (finance)
- `ydk.gov.tr` (government)
- `ydk.gov.tr` (government)

## Proposal — 432 host(s) dead in both rounds

This is a proposal, not a deletion. Applying it means adding the host to
`rules.json` → `drop.hosts` with a reason that cites this evidence, then
regenerating the catalog.

| Category | Host | Parent also dead |
| :--- | :--- | :--- |
| finance | `24banking.md` | — |
| finance | `3ds.mdmbank.ru` | — |
| finance | `abl.agrocombank.com.ua` | — |
| finance | `acs-visa.norvik.eu` | — |
| finance | `acs2.rosbank.modirum.com` | — |
| government | `acsap.saglik.gov.tr` | — |
| gaming | `activision.digital` | — |
| ads | `ad.atdmt.com` | — |
| finance | `agranisme.org` | — |
| government | `ailevecalisma.gov.tr` | — |
| government | `ankara-bel.gov.tr` | — |
| government | `ankasm.gov.tr` | — |
| finance | `atb-online.ru` | — |
| software | `azure-e2e.com` | — |
| finance | `b2.ndb24.ru` | — |
| finance | `baker.ebanksepah.ir` | — |
| finance | `bancaenlinea.bicentenariobu.com` | — |
| finance | `bancrecerdigital.com` | — |
| finance | `bank.akbtb.ru` | — |
| finance | `bank.postil.com` | — |
| finance | `bank.taatta.ru` | — |
| finance | `banking.ksk-stade.de` | — |
| finance | `banking.sparkasse-mittelsachsen.de` | — |
| finance | `banking.sparkasse-nienburg.de` | — |
| finance | `banking.sparkasse-prignitz.de` | — |
| finance | `bankingportal.sparkasse-koelnbonn.de` | — |
| finance | `bankrbk24.kz` | — |
| finance | `banksilkway.az` | — |
| government | `bayindirlik.gov.tr` | — |
| finance | `bbancobmg.com.br` | — |
| finance | `bc.bankdolinsk.ru` | — |
| finance | `bc.banksmb.ru` | — |
| finance | `bc.invb.ru` | — |
| finance | `bc.kbmkb.ru` | — |
| finance | `bc.mbr.ru` | — |
| finance | `bic.modulbank.ru` | — |
| finance | `biznes.platinumbank.com.ua` | — |
| finance | `bk.nico-bank.ru` | — |
| finance | `bk.tetrapolis.spb.ru` | — |
| finance | `bk17.ncubank.ru` | — |
| gaming | `blizzard.ru` | — |
| government | `bogazzliyan.bel.tr` | — |
| finance | `brokers.tcsbank.ru` | — |
| government | `bsec.gov.tr` | — |
| finance | `bsi.sevnb.ru` | — |
| finance | `bsm.co.id` | — |
| finance | `bss.novahovcb.ru` | — |
| gaming | `bubble-witch.com` | — |
| gaming | `bubble-witch.net` | — |
| gaming | `bubble-witch.org` | — |
| gaming | `bubblewitch.cn` | — |
| gaming | `bubblewitch.community` | — |
| gaming | `bubblewitch.guide` | — |
| gaming | `bubblewitch.jp` | — |
| gaming | `bubblewitch.net` | — |
| gaming | `bubblewitch.org` | — |
| gaming | `bubblewitch.ru` | — |
| finance | `cabinet.altbb.ru` | — |
| gaming | `candy-crush.cn` | — |
| gaming | `candy-crush.guru` | — |
| gaming | `candy-crush.jp` | — |
| gaming | `candy-crush.net` | — |
| gaming | `candy-crush.org` | — |
| gaming | `candy-crush.xyz` | — |
| gaming | `candy.game` | — |
| gaming | `candycrush.biz` | — |
| gaming | `candycrush.casa` | — |
| gaming | `candycrush.cl` | — |
| gaming | `candycrush.club` | — |
| gaming | `candycrush.community` | — |
| gaming | `candycrush.fans` | — |
| gaming | `candycrush.game` | — |
| gaming | `candycrush.gratis` | — |
| gaming | `candycrush.guide` | — |
| gaming | `candycrush.guru` | — |
| gaming | `candycrush.jp` | — |
| gaming | `candycrush.ninja` | — |
| gaming | `candycrush.support` | — |
| finance | `card.cyberplat.ru` | — |
| finance | `card2card.mkb.ru` | — |
| finance | `cardhouse.ncc-uc.ru` | — |
| finance | `cb.comertbank.md` | — |
| finance | `cb.credit-optima.com.ua` | — |
| finance | `cb.mosexibank.ru` | — |
| government | `cevreorman.gov.tr` | — |
| finance | `checkout.wirecard.com` | — |
| finance | `cimbclicks.co.id` | — |
| finance | `clb.olmabank.ru` | — |
| finance | `client.mdmbank.ru` | — |
| finance | `client.yarinterbank.ru` | — |
| finance | `connect.rtb.ru` | — |
| finance | `corpclb.bank-premium.com` | — |
| finance | `correqts.kedrbank.com` | — |
| government | `corumortakoy.bel.tr` | — |
| finance | `county2.riverbank.co.ke` | — |
| software | `cpms.spop10.ams.plex.bz` | — |
| software | `cpms35.spop10.ams.plex.bz` | — |
| gaming | `crash.mobi` | — |
| finance | `dbo.eab.ru` | — |
| finance | `dbo.energomashbank.ru` | — |
| finance | `dbo.kbmsb.ru` | — |
| finance | `dbo.metcombank.ru` | — |
| finance | `dbo.mnhb.ru` | — |
| finance | `dbo.rtbk.ru` | — |
| finance | `dbo.rublev.ru` | — |
| video | `dcs-vod.apis.anvato.net` | — |
| finance | `delsuronline.com.ve` | — |
| finance | `delta-online.kz` | — |
| government | `devletlisan.gov.tr` | — |
| gaming | `diablo.ru` | — |
| finance | `diamantpay.com.ua` | — |
| finance | `dvbank.ua` | — |
| finance | `e-bdv.banvenez.com` | — |
| finance | `e-pastabanka.lv` | — |
| finance | `e-plat.mdmbank.com` | — |
| finance | `eb.sbhr.hr` | — |
| finance | `ebank.agribank.com.tw` | — |
| finance | `ebank.ansarbank.com` | — |
| finance | `ebank.eximbank.ro` | — |
| finance | `ebankas.danskebank.lt` | — |
| finance | `ebanking.bawagpsk.com` | — |
| finance | `efactoring.ru` | — |
| finance | `efectivo.bnc.com.ve` | — |
| finance | `emobias.md` | — |
| government | `etkk.gov.tr` | — |
| finance | `eurocitybank-onlinebanking.de` | — |
| finance | `exchange.futureswap.com` | — |
| video | `f1.media.brightcove.com` | — |
| finance | `factoring.seb.de` | — |
| gaming | `farm-heroes.cn` | — |
| gaming | `farm-heroes.co.kr` | — |
| gaming | `farm-heroes.com` | — |
| gaming | `farm-heroes.kr` | — |
| gaming | `farm-heroes.net` | — |
| gaming | `farm-heroes.org` | — |
| gaming | `farm-heroes.ru` | — |
| gaming | `farmheroes.club` | — |
| gaming | `farmheroes.cn` | — |
| gaming | `farmheroes.co.kr` | — |
| gaming | `farmheroes.community` | — |
| gaming | `farmheroes.fans` | — |
| gaming | `farmheroes.guide` | — |
| gaming | `farmheroes.jp` | — |
| gaming | `farmheroes.net` | — |
| gaming | `farmheroes.org` | — |
| gaming | `farmheroes.ru` | — |
| education | `fatih.edu.tr` | — |
| finance | `fbtonline.net` | — |
| finance | `fidomarket.ua` | — |
| finance | `fr.banquepopulaire.cyberplus` | — |
| finance | `gc3d.georgiancard.ge` | — |
| government | `gelendost.bel.tr` | — |
| government | `gevas.bel.tr` | — |
| gaming | `guitarhero.asia` | — |
| government | `gunyuzu.bel.tr` | — |
| government | `hasanbeyli.bel.tr` | — |
| finance | `hawho.tw` | — |
| finance | `hb.aibank.co.il` | — |
| finance | `hc24.by` | — |
| government | `hizan.bel.tr` | — |
| finance | `homebank.tj` | — |
| finance | `i-bank.kb-rtb.ru` | — |
| finance | `i.kredprombank.ru` | — |
| finance | `i.mdm.ru` | — |
| finance | `ib.apkbank.ru` | — |
| finance | `ib.aversbank.ru` | — |
| finance | `ib.baltikums.eu` | — |
| finance | `ib.bank-maskan.ir` | — |
| finance | `ib.bankmandiri.co.id` | — |
| finance | `ib.emb.spb.ru` | — |
| finance | `ib.expobank.eu` | — |
| finance | `ib.gorbank.spb.ru` | — |
| finance | `ib.homecredit.ru` | — |
| finance | `ib.nevskybank.ru` | — |
| finance | `ib.novobank.ru` | — |
| finance | `ib.nvkbank.ru` | — |
| finance | `ibank.akibank.ru` | — |
| finance | `ibank.apabank.ru` | — |
| finance | `ibank.arsenal.ru` | — |
| finance | `ibank.asbank.ru` | — |
| finance | `ibank.aspectbank.ru` | — |
| finance | `ibank.atcib.com.ua` | — |
| finance | `ibank.bank-accent.ru` | — |
| finance | `ibank.bank-hlynov.ru` | — |
| finance | `ibank.bankmandiri.co.id` | — |
| finance | `ibank.banksbrr.ru` | — |
| finance | `ibank.belsocbank.ru` | — |
| finance | `ibank.bkbank.ru` | — |
| finance | `ibank.buguruslan.ru` | — |
| finance | `ibank.che.sevcred.ru` | — |
| finance | `ibank.dhb.ru` | — |
| finance | `ibank.economiks.ru` | — |
| finance | `ibank.eka-bank.ru` | — |
| finance | `ibank.fast.org.tw` | — |
| finance | `ibank.finprombank.ru` | — |
| finance | `ibank.forbank.ru` | — |
| finance | `ibank.fortbank.com.ua` | — |
| finance | `ibank.forusbank.ru` | — |
| finance | `ibank.gazbank.ru` | — |
| finance | `ibank.grisbank.ru` | — |
| finance | `ibank.interkb.ru` | — |
| finance | `ibank.interprombank.ru` | — |
| finance | `ibank.ipoteka-tut.ru` | — |
| finance | `ibank.isbank.ru` | — |
| finance | `ibank.izhcombank.ru` | — |
| finance | `ibank.jtbank.ru` | — |
| finance | `ibank.kbumb.ru` | — |
| finance | `ibank.khmb.ru` | — |
| finance | `ibank.kkapb.ru` | — |
| finance | `ibank.ksgbank.com.ua` | — |
| finance | `ibank.kzibank.kz` | — |
| finance | `ibank.lightbank.ru` | — |
| finance | `ibank.mcombank.ru` | — |
| finance | `ibank.metallurgbank.ru` | — |
| finance | `ibank.mia.ru` | — |
| finance | `ibank.miko-bank.ru` | — |
| finance | `ibank.mistobank.com.ua` | — |
| finance | `ibank.mrbank.ru` | — |
| finance | `ibank.necklace.ru` | — |
| finance | `ibank.npbank.ru` | — |
| finance | `ibank.nz.ru` | — |
| finance | `ibank.obrbank.ru` | — |
| finance | `ibank.paritetbank.by` | — |
| finance | `ibank.plus-bank.ru` | — |
| finance | `ibank.priscocb.ru` | — |
| finance | `ibank.promregion.ru` | — |
| finance | `ibank.rentabank.ru` | — |
| finance | `ibank.ritzbank.ru` | — |
| finance | `ibank.roscap.ru` | — |
| finance | `ibank.rtsbank.ru` | — |
| finance | `ibank.runabank.ru` | — |
| finance | `ibank.spb.nz.ru` | — |
| finance | `ibank.spiritbank.ru` | — |
| finance | `ibank.stalbank.ru` | — |
| finance | `ibank.strat.ru` | — |
| finance | `ibank.tatsotsbank.ru` | — |
| finance | `ibank.tfbank.ru` | — |
| finance | `ibank.ussurybank.ru` | — |
| finance | `ibank.vladprombank.ru` | — |
| finance | `ibank.vstcb.ru` | — |
| finance | `ibank.vvbank.ru` | — |
| finance | `ibank.ykb.ru` | — |
| finance | `ibank2.eubank.ru` | — |
| finance | `ibank2.intercredit.org` | — |
| finance | `ibank2.intercredit.ru` | — |
| finance | `ibank2.ndbank.ru` | — |
| finance | `ibank2.newtimebank.ru` | — |
| finance | `ibank2.preodbank.ru` | — |
| finance | `ibank2.stkbank.ru` | — |
| finance | `ibank2.vvbank-msk.ru` | — |
| finance | `ibank24.kz` | — |
| finance | `ibank2r.vfbank.ru` | — |
| finance | `ibankrez.kremlinbank.ru` | — |
| finance | `ibc.orgbank.ru` | — |
| finance | `ic.nw1ab.ru` | — |
| finance | `ic.vitabank.spb.ru` | — |
| finance | `ic.zhilcredit.ru` | — |
| finance | `iclient.devoncredit.ru` | — |
| finance | `iclient2.devoncredit.ru` | — |
| finance | `iclient3.devoncredit.ru` | — |
| finance | `icon25-bank.com` | — |
| finance | `ideabank24.by` | — |
| government | `iibk.gov.tr` | — |
| finance | `ikb.uci-bank.com` | — |
| finance | `imoneybank.ru` | — |
| finance | `info-msk.rusfinance.ru` | — |
| finance | `info.baikalinvestbank.ru` | — |
| finance | `info.cyberplat.ru` | — |
| finance | `internet-banking.dbsbank.in` | — |
| finance | `investbank2.com.ua` | — |
| government | `ispartaaksu.bel.tr` | — |
| government | `istanbul-gsim.gov.tr` | — |
| finance | `jcfbd.org` | — |
| government | `karacasuaydin.bel.tr` | — |
| government | `karakecili.bel.tr` | — |
| government | `karayazi.bel.tr` | — |
| government | `karliovabelediyesi.bel.tr` | — |
| gaming | `king.bingo` | — |
| gaming | `king.games` | — |
| gaming | `king.gratis` | — |
| gaming | `king.juegos` | — |
| gaming | `king.tienda` | — |
| government | `kirsehirakpinar.bel.tr` | — |
| finance | `kontrakt.ua` | — |
| finance | `ks-bank.ru` | — |
| finance | `kurskprombank.ru` | — |
| finance | `lgn.ru` | — |
| finance | `life.homecredit.ru` | — |
| finance | `link.otkritiefc.ru` | — |
| finance | `lkv02.ru` | — |
| finance | `login.sebbank.ru` | — |
| finance | `m24.comertbank.md` | — |
| finance | `manimo.su` | — |
| finance | `marfinbank.ua` | — |
| finance | `master-capital.org` | — |
| government | `mazgirt.bel.tr` | — |
| finance | `megapay.sviaz-bank.ru` | — |
| software | `meta-db-worker02.pop.ric.plex.bz` | — |
| software | `meta.plex.bz` | — |
| finance | `metabankonline.com.ua` | — |
| finance | `mib.devoncredit.ru` | — |
| gaming | `midasplayer.io` | — |
| finance | `moj.raiffeisenpolbank.com` | — |
| finance | `money.comepay.ru` | — |
| finance | `mpaycard.ru` | — |
| finance | `mtochka.com` | — |
| government | `mucurbelediyesi.bel.tr` | — |
| finance | `my.credit-agricole.com.ua` | — |
| finance | `my.europlanbank.ru` | — |
| finance | `my.morskoybank.com` | — |
| finance | `my.sjpbank.co.uk` | — |
| finance | `mybank.fortebank.com` | — |
| finance | `mycredit.platinumbank.com.ua` | — |
| gaming | `neversoft.com` | — |
| finance | `new.mybank.by` | — |
| finance | `newvelocity.ocbcnisp.com` | — |
| software | `node.plexapp.com` | — |
| finance | `ofc.ru` | — |
| government | `ohal.gov.tr` | — |
| finance | `old.taatta.ru` | — |
| finance | `old1.elecsnet.ru` | — |
| travel | `onboardwifi.flytap.com` | — |
| finance | `online.avtogradbank.ru` | — |
| finance | `online.bankcard.ru` | — |
| finance | `online.bankpozitiv.kz` | — |
| finance | `online.bm.ru` | — |
| finance | `online.bta-kazan.ru` | — |
| finance | `online.btabank.by` | — |
| finance | `online.capitalbank.kz` | — |
| finance | `online.citi.eu` | — |
| finance | `online.credit-agricole.ua` | — |
| finance | `online.exi-bank.ru` | — |
| finance | `online.fincap.ru` | — |
| finance | `online.fortebank.com` | — |
| finance | `online.isbmsk.ru` | — |
| finance | `online.metcom.ru` | — |
| finance | `online.pchrb.ru` | — |
| finance | `online.rccf.ua` | — |
| finance | `online.sevcred.ru` | — |
| finance | `online.tfb.ru` | — |
| finance | `online.vtb-bank.kz` | — |
| finance | `onlinebanking-equinetbank.de` | — |
| finance | `onlinebanking-meine-bank.de` | — |
| finance | `onlinebanking-psd-karlsruhe-neustadt.de` | — |
| finance | `onlinebanking-raiba-tuengental.de` | — |
| finance | `onlinebanking-rb-beuerberg.de` | — |
| finance | `onlinebanking-schroederbank.de` | — |
| finance | `onlinebanking.bank-credit-suisse-moscow.ru` | — |
| finance | `onlinetsb.kz` | — |
| finance | `operbank.hu` | — |
| government | `orman.gov.tr` | — |
| government | `ormansu.gov.tr` | — |
| finance | `oschad24.com` | — |
| finance | `otkritie.rapida.ru` | — |
| finance | `p2p.alfabank.ua` | — |
| finance | `p2p.mdm.ru` | — |
| gaming | `papapear.cn` | — |
| gaming | `papapear.community` | — |
| gaming | `papapear.jp` | — |
| gaming | `papapear.net` | — |
| gaming | `papapear.org` | — |
| gaming | `papapear.ru` | — |
| finance | `pay.alfabank.ua` | — |
| finance | `pay.fidobank.ua` | — |
| finance | `pay.smartbank.ua` | — |
| finance | `paycard.beeline.ru` | — |
| finance | `payeer.com` | — |
| government | `pervari.bel.tr` | — |
| gaming | `petrescue.cn` | — |
| gaming | `petrescue.community` | — |
| gaming | `petrescue.guide` | — |
| finance | `pf.comertbank.md` | — |
| finance | `pg.eazy2pay.com` | — |
| finance | `prbkbr-ibank2.ru` | — |
| finance | `promo.concord.ua` | — |
| software | `proxy.plex.bz` | — |
| software | `proxy02.pop.ord.plex.bz` | — |
| gaming | `radical.mobi` | — |
| finance | `raiffeisenbank-urbach.de` | — |
| finance | `rb-emtmannsberg.de` | — |
| finance | `retail.mvbank.ru` | — |
| finance | `retail.nrb.ru` | — |
| finance | `retail.sdm.ru` | — |
| finance | `rosmicrocredit.ru` | — |
| gaming | `royalgames.name` | — |
| finance | `rsportal.kbca.ru` | — |
| finance | `sberbank.kz` | — |
| finance | `sdk-stockhausen.de` | — |
| finance | `secure.bnc.com.ve` | — |
| finance | `secure.bnpparibas.net` | — |
| finance | `secure.commercegate.com` | — |
| finance | `secure.ideabank.pl` | — |
| finance | `secure.ipsp.com` | — |
| finance | `secure.paygateway.ru` | — |
| finance | `secure.payu.com.tr` | — |
| finance | `secure.tcsbank.ru` | — |
| finance | `secureshop.firstdata.lv` | — |
| government | `shcek.gov.tr` | — |
| finance | `sibes.omsk.ru` | — |
| government | `sivasakincilar.bel.tr` | — |
| government | `ssk-ank.gov.tr` | — |
| gaming | `starcraft.ru` | — |
| finance | `static.siteheart.com` | — |
| government | `tapu.gov.tr` | — |
| ads | `tc.tradetracker.com` | — |
| government | `teas.gov.tr` | — |
| finance | `telebank.eatpbank.ru` | — |
| finance | `telebank.forshtadt.ru` | — |
| finance | `telebank.tatsotsbank.ru` | — |
| finance | `teleweb.sdmnet.ru` | — |
| finance | `terminal.accentpay.com` | — |
| finance | `th.bibplus.uobgroup.com` | — |
| finance | `ticket.uz.gov.ua` | — |
| finance | `titubb.titck.gov.tr` | — |
| government | `todaie.gov.tr` | — |
| finance | `ucpb.biz` | — |
| government | `uludere.bel.tr` | — |
| finance | `unison24.com.ua` | — |
| finance | `upay.megafon.ru` | — |
| government | `uzumlu24.bel.tr` | — |
| government | `van-gurpinar.bel.tr` | — |
| government | `vanmuradiye.bel.tr` | — |
| finance | `vip.ritzbank.ru` | — |
| finance | `vivuso.ru` | — |
| finance | `vostok.bank` | — |
| finance | `wallet.btc.com` | — |
| gaming | `warcraft.co.kr` | — |
| finance | `wfc.sebank.se` | — |
| travel | `wifi.finnair.com` | — |
| finance | `www4.handelsbanken.fi` | — |
| government | `yeni.atasehir.bel.tr` | — |
| finance | `yenibayi.passotaksit.com.tr` | — |
