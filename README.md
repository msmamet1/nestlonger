# NestLonger

## What This Is

NestLonger is an early-stage venture that helps adult children get ahead of the problem of aging parents who want to stay in their homes. It connects families with certified professionals for the practical steps that make aging at home safe, affordable, and doable - before a crisis forces their hand.

The business model is a demand generation platform operating as a multi-vertical lead generation and referral business. The model is inspired by CSN Stores (which became Wayfair) - discrete category verticals that operate independently under a shared brand, each with their own supply partners and economics, with a coordination layer added later once verticals are cash-flow positive.

## Founder

Matthew Mamet - fractional Chief Growth Officer and product strategist. Deep experience in marketplaces, lead generation, and consumer platforms including TripAdvisor (e-commerce, 0 to $200M), EverQuote (insurance marketplace, multiple verticals), EnergySage (solar marketplace, product lead), and HouseAccount (home services marketplace).

## Business Model

Path B: lean AI-native demand generation machine. Not a venture-backed platform build. Target: $500K net profit, operating near-solo with agentic infrastructure.

Reference models: EnergySage, EverQuote, TripAdvisor applied to the aging-in-place category. Own homeowner intent via content and AEO (AI engine optimization), sell pre-educated high-intent leads to supply-side partners at premium referral rates.

## Current Stage

Early validation. Brand foundations locked May 2026. First vertical (grab bars) in build. Fractional client work funds the build while passive revenue scales.

## Active Verticals

### Vertical 1 - Grab Bars (Sandbox / Learning)
- URL: nestlonger.com/grab-bars
- Supply partner: Louis Tenenbaum / HomesRenewed (SBIR-funded grab bar installation app, certified installer network)
- Revenue model: referral fee per completed installation
- Goal: learn acquisition tactics and agentic ops, go net positive. Not a $500K business.
- Status: Building

### Vertical 2 - ADU Lead Generation (Primary Bet)
- URL: nestlonger.com/adus
- Supply side: ADU contractors (fragmented, hungry for pre-educated leads)
- Revenue model: 2-3% referral fee on closed projects (~$4,500 per close at $180K avg project)
- Goal: $500K net profit at 51 qualified leads/month, 20% lead-to-close rate
- Status: Planning

## Financial Target

- Net profit goal: $500,000/year
- Model: $548K gross revenue required at $48K annual OpEx
- ADU path: 122 closed deals/year, 610 qualified leads/year, 51 leads/month
- Timeline: Month 1-4 sandbox, Month 4-12 ADU launch, Month 12-24 scale to target

## Brand

- Positioning: Trusted guide for adult children helping aging parents stay home safely
- Tagline (functional): Stay home, safely.
- Tagline (hero): The home you love, for as long as possible.
- Tone: Clear. Warm. Practical.
- Primary audience: Adult children (45-60) with aging parents
- Never say: loved one, senior, elderly, end of life
- Always say: aging parent, your mom, your dad, get ahead of it

Full brand guide: `/brand/brand-guide.md`

## Tech Stack

- Site: Static HTML / CSS deployed on Netlify (nestlonger.com)
- Lead capture: Simple form with zip, who are you helping, what do you need, email
- Agentic infrastructure: Make.com, Apify, Claude API, webhooks
- CMS: TBD (Ghost considered)
- Analytics: TBD

## Key Supply Relationships

- **Louis Tenenbaum / HomesRenewed** - 30+ year aging-in-place remodeling expert, SBIR grant for grab bar installation app, certified installer network, UnitedHealthcare reimbursement relationships. Actively seeking go-to-market co-founder.
- **ADU contractors** - TBD. Need 3-5 signed before ADU vertical launches.

## Key Insights from Research (21 Listening Tour Meetings)

- Adult children are the buyer, not the aging parent
- The vitamin-not-painkiller problem is structural - grab bars solve it because someone just fell or is scared they will
- Customer acquisition cost is the historical killer of companies in this space
- Insurance reimbursement (Medicare Advantage, UnitedHealthcare, VA benefits) is an underutilized acquisition channel
- AEO / AI engine optimization is the distribution bet - Casey Winters: "ChatGPT will say there's a company that handles all of this, do you want me to book an appointment? 90% conversion rate"
- Grab bar installation reduces falls 80% (Ohio EMS pilot data, HomesRenewed)
- 93% of older Canadians would accept a free grab bar if offered (Canadian study)
- ADU for multigenerational living is 42% of total ADU demand - aging-in-place angle is real

## Repository Structure

```
nestlonger/
- brand/
  - brand-guide.md
  - brand-guide.html
- copy/
  - positioning.md
  - voice-and-tone.md
  - verticals/
    - grab-bars.md
    - adu.md
- pages/
  - grab-bars/
    - index.html
    - content-briefs.md
- research/
  - listening-tour-synthesis.md
- strategy/
  - venture-strategy.md
- README.md
```

## Instructions for AI Assistants

Read this README first. Then read the relevant vertical brief in `/copy/verticals/` before writing any copy or building any page. All pages must follow the brand guide in `/brand/brand-guide.md`. Never deviate from the voice rules - especially the never-say list. The buyer is always the adult child, not the aging parent.
