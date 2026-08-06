package puzzle.math;
import puzzle.Puzzle;

/**
 * Encode a (latitude, longitude) pair into a geohash string.
 * Approach: Repeatedly bisect the lat/lon ranges, interleave the resulting bits, and emit base-32
 * characters.
 * Complexity: Time O(precision), Space O(1).
 */
public class GeoHashPuzzle implements Puzzle {
    /**
     * Standard geohash alphabet (omits visually confusing letters such as a, i, l, o).
     */
    private static final char[] BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz".toCharArray();

    /**
     * Encode one sample coordinate pair and print the resulting geohash.
     */
    @Override
    public void resolve() {
        int precision = 5;
        char[] geohash = new char[precision + 1];               // +1 for the trailing terminator
        encode_geohash(42.6, -5.6, precision, geohash);
        System.out.println("geohash(42.6, -5.6) = " + new String(geohash, 0, precision));   // -> ezs42
    }

    /**
     * Encode one (latitude, longitude) pair into a geohash of the requested precision. Longitude
     * and latitude intervals are repeatedly bisected, their bits are interleaved, and every 5 bits
     * are emitted through the base32 alphabet.
     */
    private static void encode_geohash(double latitude, double longitude, int precision, char[] geohash) {
        boolean is_even = true;
        int i = 0;
        double[] lat = new double[2];
        double[] lon = new double[2];
        double mid;
        char[] bits = {16, 8, 4, 2, 1};
        int bit = 0;
        int ch = 0;
        lat[0] = -90.0;
        lat[1] = 90.0;
        lon[0] = -180.0;
        lon[1] = 180.0;
        while (i < precision) {
            if (is_even) {
                mid = (lon[0] + lon[1]) / 2;
                if (longitude > mid) {
                    ch |= bits[bit];
                    lon[0] = mid;
                } else {
                    lon[1] = mid;
                }
            } else {
                mid = (lat[0] + lat[1]) / 2;
                if (latitude > mid) {
                    ch |= bits[bit];
                    lat[0] = mid;
                } else {
                    lat[1] = mid;
                }
            }
            is_even = !is_even;
            if (bit < 4) {
                bit++;
            } else {
                geohash[i++] = BASE32[ch];
                bit = 0;
                ch = 0;
            }
        }
        geohash[i] = 0;
    }
}
