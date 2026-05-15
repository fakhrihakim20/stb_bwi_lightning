# VIII. Conclusion

We have presented a per-tower lightning GFD forecast for the 281
towers of the 150&nbsp;kV Situbondo--Banyuwangi corridor, on a seven-
year Vaisala FALLS dataset, framed as an explicit two-model
comparison. **Model&nbsp;C** is the conservative statistically-honest
benchmark: AICc-selected, equal annual weighting, James--Stein
shrunken per-tower shares. **Model&nbsp;D** is the forecast-informed
planning instrument: recency-weighted, forced climate coefficients,
ridge spatial correction. The two models trade CV skill for climate
responsiveness in a deliberate way --- Model&nbsp;D pays a 20&nbsp;%
RMSE penalty for a 37&nbsp;% La&nbsp;Niña-to-El&nbsp;Niño scenario
spread that Model&nbsp;C cannot produce.

Operationally, both models identify the same 16-tower foothill
cluster at Mt.&nbsp;Ijen (Jaccard 0.67) as the priority for arrester
upgrades, while Model&nbsp;D additionally quantifies the climate-driven
maintenance-scheduling response that PLN's existing operational
ENSO outlooks already imply.

The work is published as a reproducible pipeline rather than as a
finished forecast. With $n = 7$, no statistical inference is
conclusive; the right next step is the 2026 observed-versus-forecast
comparison, scheduled for January 2027, which will provide the first
genuinely prospective skill check.

# References

[1] IEEE Standards Association, *IEEE Guide for Improving the Lightning
Performance of Electric Power Overhead Distribution Lines*,
IEEE Std 1410-2010, 2010.

[2] IEEE Standards Association, *IEEE Guide for Improving the Lightning
Performance of Transmission Lines*, IEEE Std 1243-1997, 1997.

[3] J. M. Hilbe, *Negative Binomial Regression*, 2nd ed.,
Cambridge University Press, 2011.

[4] B. Efron and C. Morris, "Stein's paradox in statistics,"
*Scientific American*, vol. 236, no. 5, pp. 119--127, 1977.

[5] L. Kish, *Survey Sampling*, John Wiley & Sons, 1965.

[6] A. E. Hoerl and R. W. Kennard, "Ridge regression: Biased estimation
for nonorthogonal problems," *Technometrics*, vol. 12, no. 1,
pp. 55--67, 1970.

[7] E. Aldrian and R. D. Susanto, "Identification of three dominant
rainfall regions within Indonesia and their relationship to sea
surface temperature," *International Journal of Climatology*,
vol. 23, no. 12, pp. 1435--1452, 2003.

[8] R. I. Albrecht, S. J. Goodman, D. E. Buechler, R. J. Blakeslee,
and H. J. Christian, "Where are the lightning hotspots on Earth?"
*Bulletin of the American Meteorological Society*, vol. 97, no. 11,
pp. 2051--2068, 2016.

[9] H. J. Christian *et al.*, "Global frequency and distribution of
lightning as observed from space by the Optical Transient Detector,"
*Journal of Geophysical Research: Atmospheres*, vol. 108, no. D1,
p. 4005, 2003.

[10] [REFNEEDED: Indonesia-specific lightning-ENSO study, if available]

[11] NOAA Physical Sciences Laboratory, Niño 3.4 SST Index,
https://psl.noaa.gov/data/correlation/nina34.anom.data, accessed 2026.

[12] HadISST Indian Ocean Dipole DMI Index,
https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data,
accessed 2026.

[13] Source repository:
https://github.com/fakhrihakim20/stb_bwi_lightning, accessed 2026.
