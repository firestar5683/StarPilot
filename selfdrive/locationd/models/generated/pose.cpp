#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_7754318151462489406) {
   out_7754318151462489406[0] = delta_x[0] + nom_x[0];
   out_7754318151462489406[1] = delta_x[1] + nom_x[1];
   out_7754318151462489406[2] = delta_x[2] + nom_x[2];
   out_7754318151462489406[3] = delta_x[3] + nom_x[3];
   out_7754318151462489406[4] = delta_x[4] + nom_x[4];
   out_7754318151462489406[5] = delta_x[5] + nom_x[5];
   out_7754318151462489406[6] = delta_x[6] + nom_x[6];
   out_7754318151462489406[7] = delta_x[7] + nom_x[7];
   out_7754318151462489406[8] = delta_x[8] + nom_x[8];
   out_7754318151462489406[9] = delta_x[9] + nom_x[9];
   out_7754318151462489406[10] = delta_x[10] + nom_x[10];
   out_7754318151462489406[11] = delta_x[11] + nom_x[11];
   out_7754318151462489406[12] = delta_x[12] + nom_x[12];
   out_7754318151462489406[13] = delta_x[13] + nom_x[13];
   out_7754318151462489406[14] = delta_x[14] + nom_x[14];
   out_7754318151462489406[15] = delta_x[15] + nom_x[15];
   out_7754318151462489406[16] = delta_x[16] + nom_x[16];
   out_7754318151462489406[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5172808168415891616) {
   out_5172808168415891616[0] = -nom_x[0] + true_x[0];
   out_5172808168415891616[1] = -nom_x[1] + true_x[1];
   out_5172808168415891616[2] = -nom_x[2] + true_x[2];
   out_5172808168415891616[3] = -nom_x[3] + true_x[3];
   out_5172808168415891616[4] = -nom_x[4] + true_x[4];
   out_5172808168415891616[5] = -nom_x[5] + true_x[5];
   out_5172808168415891616[6] = -nom_x[6] + true_x[6];
   out_5172808168415891616[7] = -nom_x[7] + true_x[7];
   out_5172808168415891616[8] = -nom_x[8] + true_x[8];
   out_5172808168415891616[9] = -nom_x[9] + true_x[9];
   out_5172808168415891616[10] = -nom_x[10] + true_x[10];
   out_5172808168415891616[11] = -nom_x[11] + true_x[11];
   out_5172808168415891616[12] = -nom_x[12] + true_x[12];
   out_5172808168415891616[13] = -nom_x[13] + true_x[13];
   out_5172808168415891616[14] = -nom_x[14] + true_x[14];
   out_5172808168415891616[15] = -nom_x[15] + true_x[15];
   out_5172808168415891616[16] = -nom_x[16] + true_x[16];
   out_5172808168415891616[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2254475305049299983) {
   out_2254475305049299983[0] = 1.0;
   out_2254475305049299983[1] = 0.0;
   out_2254475305049299983[2] = 0.0;
   out_2254475305049299983[3] = 0.0;
   out_2254475305049299983[4] = 0.0;
   out_2254475305049299983[5] = 0.0;
   out_2254475305049299983[6] = 0.0;
   out_2254475305049299983[7] = 0.0;
   out_2254475305049299983[8] = 0.0;
   out_2254475305049299983[9] = 0.0;
   out_2254475305049299983[10] = 0.0;
   out_2254475305049299983[11] = 0.0;
   out_2254475305049299983[12] = 0.0;
   out_2254475305049299983[13] = 0.0;
   out_2254475305049299983[14] = 0.0;
   out_2254475305049299983[15] = 0.0;
   out_2254475305049299983[16] = 0.0;
   out_2254475305049299983[17] = 0.0;
   out_2254475305049299983[18] = 0.0;
   out_2254475305049299983[19] = 1.0;
   out_2254475305049299983[20] = 0.0;
   out_2254475305049299983[21] = 0.0;
   out_2254475305049299983[22] = 0.0;
   out_2254475305049299983[23] = 0.0;
   out_2254475305049299983[24] = 0.0;
   out_2254475305049299983[25] = 0.0;
   out_2254475305049299983[26] = 0.0;
   out_2254475305049299983[27] = 0.0;
   out_2254475305049299983[28] = 0.0;
   out_2254475305049299983[29] = 0.0;
   out_2254475305049299983[30] = 0.0;
   out_2254475305049299983[31] = 0.0;
   out_2254475305049299983[32] = 0.0;
   out_2254475305049299983[33] = 0.0;
   out_2254475305049299983[34] = 0.0;
   out_2254475305049299983[35] = 0.0;
   out_2254475305049299983[36] = 0.0;
   out_2254475305049299983[37] = 0.0;
   out_2254475305049299983[38] = 1.0;
   out_2254475305049299983[39] = 0.0;
   out_2254475305049299983[40] = 0.0;
   out_2254475305049299983[41] = 0.0;
   out_2254475305049299983[42] = 0.0;
   out_2254475305049299983[43] = 0.0;
   out_2254475305049299983[44] = 0.0;
   out_2254475305049299983[45] = 0.0;
   out_2254475305049299983[46] = 0.0;
   out_2254475305049299983[47] = 0.0;
   out_2254475305049299983[48] = 0.0;
   out_2254475305049299983[49] = 0.0;
   out_2254475305049299983[50] = 0.0;
   out_2254475305049299983[51] = 0.0;
   out_2254475305049299983[52] = 0.0;
   out_2254475305049299983[53] = 0.0;
   out_2254475305049299983[54] = 0.0;
   out_2254475305049299983[55] = 0.0;
   out_2254475305049299983[56] = 0.0;
   out_2254475305049299983[57] = 1.0;
   out_2254475305049299983[58] = 0.0;
   out_2254475305049299983[59] = 0.0;
   out_2254475305049299983[60] = 0.0;
   out_2254475305049299983[61] = 0.0;
   out_2254475305049299983[62] = 0.0;
   out_2254475305049299983[63] = 0.0;
   out_2254475305049299983[64] = 0.0;
   out_2254475305049299983[65] = 0.0;
   out_2254475305049299983[66] = 0.0;
   out_2254475305049299983[67] = 0.0;
   out_2254475305049299983[68] = 0.0;
   out_2254475305049299983[69] = 0.0;
   out_2254475305049299983[70] = 0.0;
   out_2254475305049299983[71] = 0.0;
   out_2254475305049299983[72] = 0.0;
   out_2254475305049299983[73] = 0.0;
   out_2254475305049299983[74] = 0.0;
   out_2254475305049299983[75] = 0.0;
   out_2254475305049299983[76] = 1.0;
   out_2254475305049299983[77] = 0.0;
   out_2254475305049299983[78] = 0.0;
   out_2254475305049299983[79] = 0.0;
   out_2254475305049299983[80] = 0.0;
   out_2254475305049299983[81] = 0.0;
   out_2254475305049299983[82] = 0.0;
   out_2254475305049299983[83] = 0.0;
   out_2254475305049299983[84] = 0.0;
   out_2254475305049299983[85] = 0.0;
   out_2254475305049299983[86] = 0.0;
   out_2254475305049299983[87] = 0.0;
   out_2254475305049299983[88] = 0.0;
   out_2254475305049299983[89] = 0.0;
   out_2254475305049299983[90] = 0.0;
   out_2254475305049299983[91] = 0.0;
   out_2254475305049299983[92] = 0.0;
   out_2254475305049299983[93] = 0.0;
   out_2254475305049299983[94] = 0.0;
   out_2254475305049299983[95] = 1.0;
   out_2254475305049299983[96] = 0.0;
   out_2254475305049299983[97] = 0.0;
   out_2254475305049299983[98] = 0.0;
   out_2254475305049299983[99] = 0.0;
   out_2254475305049299983[100] = 0.0;
   out_2254475305049299983[101] = 0.0;
   out_2254475305049299983[102] = 0.0;
   out_2254475305049299983[103] = 0.0;
   out_2254475305049299983[104] = 0.0;
   out_2254475305049299983[105] = 0.0;
   out_2254475305049299983[106] = 0.0;
   out_2254475305049299983[107] = 0.0;
   out_2254475305049299983[108] = 0.0;
   out_2254475305049299983[109] = 0.0;
   out_2254475305049299983[110] = 0.0;
   out_2254475305049299983[111] = 0.0;
   out_2254475305049299983[112] = 0.0;
   out_2254475305049299983[113] = 0.0;
   out_2254475305049299983[114] = 1.0;
   out_2254475305049299983[115] = 0.0;
   out_2254475305049299983[116] = 0.0;
   out_2254475305049299983[117] = 0.0;
   out_2254475305049299983[118] = 0.0;
   out_2254475305049299983[119] = 0.0;
   out_2254475305049299983[120] = 0.0;
   out_2254475305049299983[121] = 0.0;
   out_2254475305049299983[122] = 0.0;
   out_2254475305049299983[123] = 0.0;
   out_2254475305049299983[124] = 0.0;
   out_2254475305049299983[125] = 0.0;
   out_2254475305049299983[126] = 0.0;
   out_2254475305049299983[127] = 0.0;
   out_2254475305049299983[128] = 0.0;
   out_2254475305049299983[129] = 0.0;
   out_2254475305049299983[130] = 0.0;
   out_2254475305049299983[131] = 0.0;
   out_2254475305049299983[132] = 0.0;
   out_2254475305049299983[133] = 1.0;
   out_2254475305049299983[134] = 0.0;
   out_2254475305049299983[135] = 0.0;
   out_2254475305049299983[136] = 0.0;
   out_2254475305049299983[137] = 0.0;
   out_2254475305049299983[138] = 0.0;
   out_2254475305049299983[139] = 0.0;
   out_2254475305049299983[140] = 0.0;
   out_2254475305049299983[141] = 0.0;
   out_2254475305049299983[142] = 0.0;
   out_2254475305049299983[143] = 0.0;
   out_2254475305049299983[144] = 0.0;
   out_2254475305049299983[145] = 0.0;
   out_2254475305049299983[146] = 0.0;
   out_2254475305049299983[147] = 0.0;
   out_2254475305049299983[148] = 0.0;
   out_2254475305049299983[149] = 0.0;
   out_2254475305049299983[150] = 0.0;
   out_2254475305049299983[151] = 0.0;
   out_2254475305049299983[152] = 1.0;
   out_2254475305049299983[153] = 0.0;
   out_2254475305049299983[154] = 0.0;
   out_2254475305049299983[155] = 0.0;
   out_2254475305049299983[156] = 0.0;
   out_2254475305049299983[157] = 0.0;
   out_2254475305049299983[158] = 0.0;
   out_2254475305049299983[159] = 0.0;
   out_2254475305049299983[160] = 0.0;
   out_2254475305049299983[161] = 0.0;
   out_2254475305049299983[162] = 0.0;
   out_2254475305049299983[163] = 0.0;
   out_2254475305049299983[164] = 0.0;
   out_2254475305049299983[165] = 0.0;
   out_2254475305049299983[166] = 0.0;
   out_2254475305049299983[167] = 0.0;
   out_2254475305049299983[168] = 0.0;
   out_2254475305049299983[169] = 0.0;
   out_2254475305049299983[170] = 0.0;
   out_2254475305049299983[171] = 1.0;
   out_2254475305049299983[172] = 0.0;
   out_2254475305049299983[173] = 0.0;
   out_2254475305049299983[174] = 0.0;
   out_2254475305049299983[175] = 0.0;
   out_2254475305049299983[176] = 0.0;
   out_2254475305049299983[177] = 0.0;
   out_2254475305049299983[178] = 0.0;
   out_2254475305049299983[179] = 0.0;
   out_2254475305049299983[180] = 0.0;
   out_2254475305049299983[181] = 0.0;
   out_2254475305049299983[182] = 0.0;
   out_2254475305049299983[183] = 0.0;
   out_2254475305049299983[184] = 0.0;
   out_2254475305049299983[185] = 0.0;
   out_2254475305049299983[186] = 0.0;
   out_2254475305049299983[187] = 0.0;
   out_2254475305049299983[188] = 0.0;
   out_2254475305049299983[189] = 0.0;
   out_2254475305049299983[190] = 1.0;
   out_2254475305049299983[191] = 0.0;
   out_2254475305049299983[192] = 0.0;
   out_2254475305049299983[193] = 0.0;
   out_2254475305049299983[194] = 0.0;
   out_2254475305049299983[195] = 0.0;
   out_2254475305049299983[196] = 0.0;
   out_2254475305049299983[197] = 0.0;
   out_2254475305049299983[198] = 0.0;
   out_2254475305049299983[199] = 0.0;
   out_2254475305049299983[200] = 0.0;
   out_2254475305049299983[201] = 0.0;
   out_2254475305049299983[202] = 0.0;
   out_2254475305049299983[203] = 0.0;
   out_2254475305049299983[204] = 0.0;
   out_2254475305049299983[205] = 0.0;
   out_2254475305049299983[206] = 0.0;
   out_2254475305049299983[207] = 0.0;
   out_2254475305049299983[208] = 0.0;
   out_2254475305049299983[209] = 1.0;
   out_2254475305049299983[210] = 0.0;
   out_2254475305049299983[211] = 0.0;
   out_2254475305049299983[212] = 0.0;
   out_2254475305049299983[213] = 0.0;
   out_2254475305049299983[214] = 0.0;
   out_2254475305049299983[215] = 0.0;
   out_2254475305049299983[216] = 0.0;
   out_2254475305049299983[217] = 0.0;
   out_2254475305049299983[218] = 0.0;
   out_2254475305049299983[219] = 0.0;
   out_2254475305049299983[220] = 0.0;
   out_2254475305049299983[221] = 0.0;
   out_2254475305049299983[222] = 0.0;
   out_2254475305049299983[223] = 0.0;
   out_2254475305049299983[224] = 0.0;
   out_2254475305049299983[225] = 0.0;
   out_2254475305049299983[226] = 0.0;
   out_2254475305049299983[227] = 0.0;
   out_2254475305049299983[228] = 1.0;
   out_2254475305049299983[229] = 0.0;
   out_2254475305049299983[230] = 0.0;
   out_2254475305049299983[231] = 0.0;
   out_2254475305049299983[232] = 0.0;
   out_2254475305049299983[233] = 0.0;
   out_2254475305049299983[234] = 0.0;
   out_2254475305049299983[235] = 0.0;
   out_2254475305049299983[236] = 0.0;
   out_2254475305049299983[237] = 0.0;
   out_2254475305049299983[238] = 0.0;
   out_2254475305049299983[239] = 0.0;
   out_2254475305049299983[240] = 0.0;
   out_2254475305049299983[241] = 0.0;
   out_2254475305049299983[242] = 0.0;
   out_2254475305049299983[243] = 0.0;
   out_2254475305049299983[244] = 0.0;
   out_2254475305049299983[245] = 0.0;
   out_2254475305049299983[246] = 0.0;
   out_2254475305049299983[247] = 1.0;
   out_2254475305049299983[248] = 0.0;
   out_2254475305049299983[249] = 0.0;
   out_2254475305049299983[250] = 0.0;
   out_2254475305049299983[251] = 0.0;
   out_2254475305049299983[252] = 0.0;
   out_2254475305049299983[253] = 0.0;
   out_2254475305049299983[254] = 0.0;
   out_2254475305049299983[255] = 0.0;
   out_2254475305049299983[256] = 0.0;
   out_2254475305049299983[257] = 0.0;
   out_2254475305049299983[258] = 0.0;
   out_2254475305049299983[259] = 0.0;
   out_2254475305049299983[260] = 0.0;
   out_2254475305049299983[261] = 0.0;
   out_2254475305049299983[262] = 0.0;
   out_2254475305049299983[263] = 0.0;
   out_2254475305049299983[264] = 0.0;
   out_2254475305049299983[265] = 0.0;
   out_2254475305049299983[266] = 1.0;
   out_2254475305049299983[267] = 0.0;
   out_2254475305049299983[268] = 0.0;
   out_2254475305049299983[269] = 0.0;
   out_2254475305049299983[270] = 0.0;
   out_2254475305049299983[271] = 0.0;
   out_2254475305049299983[272] = 0.0;
   out_2254475305049299983[273] = 0.0;
   out_2254475305049299983[274] = 0.0;
   out_2254475305049299983[275] = 0.0;
   out_2254475305049299983[276] = 0.0;
   out_2254475305049299983[277] = 0.0;
   out_2254475305049299983[278] = 0.0;
   out_2254475305049299983[279] = 0.0;
   out_2254475305049299983[280] = 0.0;
   out_2254475305049299983[281] = 0.0;
   out_2254475305049299983[282] = 0.0;
   out_2254475305049299983[283] = 0.0;
   out_2254475305049299983[284] = 0.0;
   out_2254475305049299983[285] = 1.0;
   out_2254475305049299983[286] = 0.0;
   out_2254475305049299983[287] = 0.0;
   out_2254475305049299983[288] = 0.0;
   out_2254475305049299983[289] = 0.0;
   out_2254475305049299983[290] = 0.0;
   out_2254475305049299983[291] = 0.0;
   out_2254475305049299983[292] = 0.0;
   out_2254475305049299983[293] = 0.0;
   out_2254475305049299983[294] = 0.0;
   out_2254475305049299983[295] = 0.0;
   out_2254475305049299983[296] = 0.0;
   out_2254475305049299983[297] = 0.0;
   out_2254475305049299983[298] = 0.0;
   out_2254475305049299983[299] = 0.0;
   out_2254475305049299983[300] = 0.0;
   out_2254475305049299983[301] = 0.0;
   out_2254475305049299983[302] = 0.0;
   out_2254475305049299983[303] = 0.0;
   out_2254475305049299983[304] = 1.0;
   out_2254475305049299983[305] = 0.0;
   out_2254475305049299983[306] = 0.0;
   out_2254475305049299983[307] = 0.0;
   out_2254475305049299983[308] = 0.0;
   out_2254475305049299983[309] = 0.0;
   out_2254475305049299983[310] = 0.0;
   out_2254475305049299983[311] = 0.0;
   out_2254475305049299983[312] = 0.0;
   out_2254475305049299983[313] = 0.0;
   out_2254475305049299983[314] = 0.0;
   out_2254475305049299983[315] = 0.0;
   out_2254475305049299983[316] = 0.0;
   out_2254475305049299983[317] = 0.0;
   out_2254475305049299983[318] = 0.0;
   out_2254475305049299983[319] = 0.0;
   out_2254475305049299983[320] = 0.0;
   out_2254475305049299983[321] = 0.0;
   out_2254475305049299983[322] = 0.0;
   out_2254475305049299983[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_9187930556967356165) {
   out_9187930556967356165[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_9187930556967356165[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_9187930556967356165[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_9187930556967356165[3] = dt*state[12] + state[3];
   out_9187930556967356165[4] = dt*state[13] + state[4];
   out_9187930556967356165[5] = dt*state[14] + state[5];
   out_9187930556967356165[6] = state[6];
   out_9187930556967356165[7] = state[7];
   out_9187930556967356165[8] = state[8];
   out_9187930556967356165[9] = state[9];
   out_9187930556967356165[10] = state[10];
   out_9187930556967356165[11] = state[11];
   out_9187930556967356165[12] = state[12];
   out_9187930556967356165[13] = state[13];
   out_9187930556967356165[14] = state[14];
   out_9187930556967356165[15] = state[15];
   out_9187930556967356165[16] = state[16];
   out_9187930556967356165[17] = state[17];
}
void F_fun(double *state, double dt, double *out_1250378920670806697) {
   out_1250378920670806697[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1250378920670806697[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1250378920670806697[2] = 0;
   out_1250378920670806697[3] = 0;
   out_1250378920670806697[4] = 0;
   out_1250378920670806697[5] = 0;
   out_1250378920670806697[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1250378920670806697[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1250378920670806697[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1250378920670806697[9] = 0;
   out_1250378920670806697[10] = 0;
   out_1250378920670806697[11] = 0;
   out_1250378920670806697[12] = 0;
   out_1250378920670806697[13] = 0;
   out_1250378920670806697[14] = 0;
   out_1250378920670806697[15] = 0;
   out_1250378920670806697[16] = 0;
   out_1250378920670806697[17] = 0;
   out_1250378920670806697[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1250378920670806697[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1250378920670806697[20] = 0;
   out_1250378920670806697[21] = 0;
   out_1250378920670806697[22] = 0;
   out_1250378920670806697[23] = 0;
   out_1250378920670806697[24] = 0;
   out_1250378920670806697[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1250378920670806697[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1250378920670806697[27] = 0;
   out_1250378920670806697[28] = 0;
   out_1250378920670806697[29] = 0;
   out_1250378920670806697[30] = 0;
   out_1250378920670806697[31] = 0;
   out_1250378920670806697[32] = 0;
   out_1250378920670806697[33] = 0;
   out_1250378920670806697[34] = 0;
   out_1250378920670806697[35] = 0;
   out_1250378920670806697[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1250378920670806697[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1250378920670806697[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1250378920670806697[39] = 0;
   out_1250378920670806697[40] = 0;
   out_1250378920670806697[41] = 0;
   out_1250378920670806697[42] = 0;
   out_1250378920670806697[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1250378920670806697[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1250378920670806697[45] = 0;
   out_1250378920670806697[46] = 0;
   out_1250378920670806697[47] = 0;
   out_1250378920670806697[48] = 0;
   out_1250378920670806697[49] = 0;
   out_1250378920670806697[50] = 0;
   out_1250378920670806697[51] = 0;
   out_1250378920670806697[52] = 0;
   out_1250378920670806697[53] = 0;
   out_1250378920670806697[54] = 0;
   out_1250378920670806697[55] = 0;
   out_1250378920670806697[56] = 0;
   out_1250378920670806697[57] = 1;
   out_1250378920670806697[58] = 0;
   out_1250378920670806697[59] = 0;
   out_1250378920670806697[60] = 0;
   out_1250378920670806697[61] = 0;
   out_1250378920670806697[62] = 0;
   out_1250378920670806697[63] = 0;
   out_1250378920670806697[64] = 0;
   out_1250378920670806697[65] = 0;
   out_1250378920670806697[66] = dt;
   out_1250378920670806697[67] = 0;
   out_1250378920670806697[68] = 0;
   out_1250378920670806697[69] = 0;
   out_1250378920670806697[70] = 0;
   out_1250378920670806697[71] = 0;
   out_1250378920670806697[72] = 0;
   out_1250378920670806697[73] = 0;
   out_1250378920670806697[74] = 0;
   out_1250378920670806697[75] = 0;
   out_1250378920670806697[76] = 1;
   out_1250378920670806697[77] = 0;
   out_1250378920670806697[78] = 0;
   out_1250378920670806697[79] = 0;
   out_1250378920670806697[80] = 0;
   out_1250378920670806697[81] = 0;
   out_1250378920670806697[82] = 0;
   out_1250378920670806697[83] = 0;
   out_1250378920670806697[84] = 0;
   out_1250378920670806697[85] = dt;
   out_1250378920670806697[86] = 0;
   out_1250378920670806697[87] = 0;
   out_1250378920670806697[88] = 0;
   out_1250378920670806697[89] = 0;
   out_1250378920670806697[90] = 0;
   out_1250378920670806697[91] = 0;
   out_1250378920670806697[92] = 0;
   out_1250378920670806697[93] = 0;
   out_1250378920670806697[94] = 0;
   out_1250378920670806697[95] = 1;
   out_1250378920670806697[96] = 0;
   out_1250378920670806697[97] = 0;
   out_1250378920670806697[98] = 0;
   out_1250378920670806697[99] = 0;
   out_1250378920670806697[100] = 0;
   out_1250378920670806697[101] = 0;
   out_1250378920670806697[102] = 0;
   out_1250378920670806697[103] = 0;
   out_1250378920670806697[104] = dt;
   out_1250378920670806697[105] = 0;
   out_1250378920670806697[106] = 0;
   out_1250378920670806697[107] = 0;
   out_1250378920670806697[108] = 0;
   out_1250378920670806697[109] = 0;
   out_1250378920670806697[110] = 0;
   out_1250378920670806697[111] = 0;
   out_1250378920670806697[112] = 0;
   out_1250378920670806697[113] = 0;
   out_1250378920670806697[114] = 1;
   out_1250378920670806697[115] = 0;
   out_1250378920670806697[116] = 0;
   out_1250378920670806697[117] = 0;
   out_1250378920670806697[118] = 0;
   out_1250378920670806697[119] = 0;
   out_1250378920670806697[120] = 0;
   out_1250378920670806697[121] = 0;
   out_1250378920670806697[122] = 0;
   out_1250378920670806697[123] = 0;
   out_1250378920670806697[124] = 0;
   out_1250378920670806697[125] = 0;
   out_1250378920670806697[126] = 0;
   out_1250378920670806697[127] = 0;
   out_1250378920670806697[128] = 0;
   out_1250378920670806697[129] = 0;
   out_1250378920670806697[130] = 0;
   out_1250378920670806697[131] = 0;
   out_1250378920670806697[132] = 0;
   out_1250378920670806697[133] = 1;
   out_1250378920670806697[134] = 0;
   out_1250378920670806697[135] = 0;
   out_1250378920670806697[136] = 0;
   out_1250378920670806697[137] = 0;
   out_1250378920670806697[138] = 0;
   out_1250378920670806697[139] = 0;
   out_1250378920670806697[140] = 0;
   out_1250378920670806697[141] = 0;
   out_1250378920670806697[142] = 0;
   out_1250378920670806697[143] = 0;
   out_1250378920670806697[144] = 0;
   out_1250378920670806697[145] = 0;
   out_1250378920670806697[146] = 0;
   out_1250378920670806697[147] = 0;
   out_1250378920670806697[148] = 0;
   out_1250378920670806697[149] = 0;
   out_1250378920670806697[150] = 0;
   out_1250378920670806697[151] = 0;
   out_1250378920670806697[152] = 1;
   out_1250378920670806697[153] = 0;
   out_1250378920670806697[154] = 0;
   out_1250378920670806697[155] = 0;
   out_1250378920670806697[156] = 0;
   out_1250378920670806697[157] = 0;
   out_1250378920670806697[158] = 0;
   out_1250378920670806697[159] = 0;
   out_1250378920670806697[160] = 0;
   out_1250378920670806697[161] = 0;
   out_1250378920670806697[162] = 0;
   out_1250378920670806697[163] = 0;
   out_1250378920670806697[164] = 0;
   out_1250378920670806697[165] = 0;
   out_1250378920670806697[166] = 0;
   out_1250378920670806697[167] = 0;
   out_1250378920670806697[168] = 0;
   out_1250378920670806697[169] = 0;
   out_1250378920670806697[170] = 0;
   out_1250378920670806697[171] = 1;
   out_1250378920670806697[172] = 0;
   out_1250378920670806697[173] = 0;
   out_1250378920670806697[174] = 0;
   out_1250378920670806697[175] = 0;
   out_1250378920670806697[176] = 0;
   out_1250378920670806697[177] = 0;
   out_1250378920670806697[178] = 0;
   out_1250378920670806697[179] = 0;
   out_1250378920670806697[180] = 0;
   out_1250378920670806697[181] = 0;
   out_1250378920670806697[182] = 0;
   out_1250378920670806697[183] = 0;
   out_1250378920670806697[184] = 0;
   out_1250378920670806697[185] = 0;
   out_1250378920670806697[186] = 0;
   out_1250378920670806697[187] = 0;
   out_1250378920670806697[188] = 0;
   out_1250378920670806697[189] = 0;
   out_1250378920670806697[190] = 1;
   out_1250378920670806697[191] = 0;
   out_1250378920670806697[192] = 0;
   out_1250378920670806697[193] = 0;
   out_1250378920670806697[194] = 0;
   out_1250378920670806697[195] = 0;
   out_1250378920670806697[196] = 0;
   out_1250378920670806697[197] = 0;
   out_1250378920670806697[198] = 0;
   out_1250378920670806697[199] = 0;
   out_1250378920670806697[200] = 0;
   out_1250378920670806697[201] = 0;
   out_1250378920670806697[202] = 0;
   out_1250378920670806697[203] = 0;
   out_1250378920670806697[204] = 0;
   out_1250378920670806697[205] = 0;
   out_1250378920670806697[206] = 0;
   out_1250378920670806697[207] = 0;
   out_1250378920670806697[208] = 0;
   out_1250378920670806697[209] = 1;
   out_1250378920670806697[210] = 0;
   out_1250378920670806697[211] = 0;
   out_1250378920670806697[212] = 0;
   out_1250378920670806697[213] = 0;
   out_1250378920670806697[214] = 0;
   out_1250378920670806697[215] = 0;
   out_1250378920670806697[216] = 0;
   out_1250378920670806697[217] = 0;
   out_1250378920670806697[218] = 0;
   out_1250378920670806697[219] = 0;
   out_1250378920670806697[220] = 0;
   out_1250378920670806697[221] = 0;
   out_1250378920670806697[222] = 0;
   out_1250378920670806697[223] = 0;
   out_1250378920670806697[224] = 0;
   out_1250378920670806697[225] = 0;
   out_1250378920670806697[226] = 0;
   out_1250378920670806697[227] = 0;
   out_1250378920670806697[228] = 1;
   out_1250378920670806697[229] = 0;
   out_1250378920670806697[230] = 0;
   out_1250378920670806697[231] = 0;
   out_1250378920670806697[232] = 0;
   out_1250378920670806697[233] = 0;
   out_1250378920670806697[234] = 0;
   out_1250378920670806697[235] = 0;
   out_1250378920670806697[236] = 0;
   out_1250378920670806697[237] = 0;
   out_1250378920670806697[238] = 0;
   out_1250378920670806697[239] = 0;
   out_1250378920670806697[240] = 0;
   out_1250378920670806697[241] = 0;
   out_1250378920670806697[242] = 0;
   out_1250378920670806697[243] = 0;
   out_1250378920670806697[244] = 0;
   out_1250378920670806697[245] = 0;
   out_1250378920670806697[246] = 0;
   out_1250378920670806697[247] = 1;
   out_1250378920670806697[248] = 0;
   out_1250378920670806697[249] = 0;
   out_1250378920670806697[250] = 0;
   out_1250378920670806697[251] = 0;
   out_1250378920670806697[252] = 0;
   out_1250378920670806697[253] = 0;
   out_1250378920670806697[254] = 0;
   out_1250378920670806697[255] = 0;
   out_1250378920670806697[256] = 0;
   out_1250378920670806697[257] = 0;
   out_1250378920670806697[258] = 0;
   out_1250378920670806697[259] = 0;
   out_1250378920670806697[260] = 0;
   out_1250378920670806697[261] = 0;
   out_1250378920670806697[262] = 0;
   out_1250378920670806697[263] = 0;
   out_1250378920670806697[264] = 0;
   out_1250378920670806697[265] = 0;
   out_1250378920670806697[266] = 1;
   out_1250378920670806697[267] = 0;
   out_1250378920670806697[268] = 0;
   out_1250378920670806697[269] = 0;
   out_1250378920670806697[270] = 0;
   out_1250378920670806697[271] = 0;
   out_1250378920670806697[272] = 0;
   out_1250378920670806697[273] = 0;
   out_1250378920670806697[274] = 0;
   out_1250378920670806697[275] = 0;
   out_1250378920670806697[276] = 0;
   out_1250378920670806697[277] = 0;
   out_1250378920670806697[278] = 0;
   out_1250378920670806697[279] = 0;
   out_1250378920670806697[280] = 0;
   out_1250378920670806697[281] = 0;
   out_1250378920670806697[282] = 0;
   out_1250378920670806697[283] = 0;
   out_1250378920670806697[284] = 0;
   out_1250378920670806697[285] = 1;
   out_1250378920670806697[286] = 0;
   out_1250378920670806697[287] = 0;
   out_1250378920670806697[288] = 0;
   out_1250378920670806697[289] = 0;
   out_1250378920670806697[290] = 0;
   out_1250378920670806697[291] = 0;
   out_1250378920670806697[292] = 0;
   out_1250378920670806697[293] = 0;
   out_1250378920670806697[294] = 0;
   out_1250378920670806697[295] = 0;
   out_1250378920670806697[296] = 0;
   out_1250378920670806697[297] = 0;
   out_1250378920670806697[298] = 0;
   out_1250378920670806697[299] = 0;
   out_1250378920670806697[300] = 0;
   out_1250378920670806697[301] = 0;
   out_1250378920670806697[302] = 0;
   out_1250378920670806697[303] = 0;
   out_1250378920670806697[304] = 1;
   out_1250378920670806697[305] = 0;
   out_1250378920670806697[306] = 0;
   out_1250378920670806697[307] = 0;
   out_1250378920670806697[308] = 0;
   out_1250378920670806697[309] = 0;
   out_1250378920670806697[310] = 0;
   out_1250378920670806697[311] = 0;
   out_1250378920670806697[312] = 0;
   out_1250378920670806697[313] = 0;
   out_1250378920670806697[314] = 0;
   out_1250378920670806697[315] = 0;
   out_1250378920670806697[316] = 0;
   out_1250378920670806697[317] = 0;
   out_1250378920670806697[318] = 0;
   out_1250378920670806697[319] = 0;
   out_1250378920670806697[320] = 0;
   out_1250378920670806697[321] = 0;
   out_1250378920670806697[322] = 0;
   out_1250378920670806697[323] = 1;
}
void h_4(double *state, double *unused, double *out_3431796064752050994) {
   out_3431796064752050994[0] = state[6] + state[9];
   out_3431796064752050994[1] = state[7] + state[10];
   out_3431796064752050994[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_1019746773741649270) {
   out_1019746773741649270[0] = 0;
   out_1019746773741649270[1] = 0;
   out_1019746773741649270[2] = 0;
   out_1019746773741649270[3] = 0;
   out_1019746773741649270[4] = 0;
   out_1019746773741649270[5] = 0;
   out_1019746773741649270[6] = 1;
   out_1019746773741649270[7] = 0;
   out_1019746773741649270[8] = 0;
   out_1019746773741649270[9] = 1;
   out_1019746773741649270[10] = 0;
   out_1019746773741649270[11] = 0;
   out_1019746773741649270[12] = 0;
   out_1019746773741649270[13] = 0;
   out_1019746773741649270[14] = 0;
   out_1019746773741649270[15] = 0;
   out_1019746773741649270[16] = 0;
   out_1019746773741649270[17] = 0;
   out_1019746773741649270[18] = 0;
   out_1019746773741649270[19] = 0;
   out_1019746773741649270[20] = 0;
   out_1019746773741649270[21] = 0;
   out_1019746773741649270[22] = 0;
   out_1019746773741649270[23] = 0;
   out_1019746773741649270[24] = 0;
   out_1019746773741649270[25] = 1;
   out_1019746773741649270[26] = 0;
   out_1019746773741649270[27] = 0;
   out_1019746773741649270[28] = 1;
   out_1019746773741649270[29] = 0;
   out_1019746773741649270[30] = 0;
   out_1019746773741649270[31] = 0;
   out_1019746773741649270[32] = 0;
   out_1019746773741649270[33] = 0;
   out_1019746773741649270[34] = 0;
   out_1019746773741649270[35] = 0;
   out_1019746773741649270[36] = 0;
   out_1019746773741649270[37] = 0;
   out_1019746773741649270[38] = 0;
   out_1019746773741649270[39] = 0;
   out_1019746773741649270[40] = 0;
   out_1019746773741649270[41] = 0;
   out_1019746773741649270[42] = 0;
   out_1019746773741649270[43] = 0;
   out_1019746773741649270[44] = 1;
   out_1019746773741649270[45] = 0;
   out_1019746773741649270[46] = 0;
   out_1019746773741649270[47] = 1;
   out_1019746773741649270[48] = 0;
   out_1019746773741649270[49] = 0;
   out_1019746773741649270[50] = 0;
   out_1019746773741649270[51] = 0;
   out_1019746773741649270[52] = 0;
   out_1019746773741649270[53] = 0;
}
void h_10(double *state, double *unused, double *out_4742817048768310237) {
   out_4742817048768310237[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_4742817048768310237[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_4742817048768310237[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7482829619336622044) {
   out_7482829619336622044[0] = 0;
   out_7482829619336622044[1] = 9.8100000000000005*cos(state[1]);
   out_7482829619336622044[2] = 0;
   out_7482829619336622044[3] = 0;
   out_7482829619336622044[4] = -state[8];
   out_7482829619336622044[5] = state[7];
   out_7482829619336622044[6] = 0;
   out_7482829619336622044[7] = state[5];
   out_7482829619336622044[8] = -state[4];
   out_7482829619336622044[9] = 0;
   out_7482829619336622044[10] = 0;
   out_7482829619336622044[11] = 0;
   out_7482829619336622044[12] = 1;
   out_7482829619336622044[13] = 0;
   out_7482829619336622044[14] = 0;
   out_7482829619336622044[15] = 1;
   out_7482829619336622044[16] = 0;
   out_7482829619336622044[17] = 0;
   out_7482829619336622044[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7482829619336622044[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7482829619336622044[20] = 0;
   out_7482829619336622044[21] = state[8];
   out_7482829619336622044[22] = 0;
   out_7482829619336622044[23] = -state[6];
   out_7482829619336622044[24] = -state[5];
   out_7482829619336622044[25] = 0;
   out_7482829619336622044[26] = state[3];
   out_7482829619336622044[27] = 0;
   out_7482829619336622044[28] = 0;
   out_7482829619336622044[29] = 0;
   out_7482829619336622044[30] = 0;
   out_7482829619336622044[31] = 1;
   out_7482829619336622044[32] = 0;
   out_7482829619336622044[33] = 0;
   out_7482829619336622044[34] = 1;
   out_7482829619336622044[35] = 0;
   out_7482829619336622044[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7482829619336622044[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7482829619336622044[38] = 0;
   out_7482829619336622044[39] = -state[7];
   out_7482829619336622044[40] = state[6];
   out_7482829619336622044[41] = 0;
   out_7482829619336622044[42] = state[4];
   out_7482829619336622044[43] = -state[3];
   out_7482829619336622044[44] = 0;
   out_7482829619336622044[45] = 0;
   out_7482829619336622044[46] = 0;
   out_7482829619336622044[47] = 0;
   out_7482829619336622044[48] = 0;
   out_7482829619336622044[49] = 0;
   out_7482829619336622044[50] = 1;
   out_7482829619336622044[51] = 0;
   out_7482829619336622044[52] = 0;
   out_7482829619336622044[53] = 1;
}
void h_13(double *state, double *unused, double *out_3124060736866225144) {
   out_3124060736866225144[0] = state[3];
   out_3124060736866225144[1] = state[4];
   out_3124060736866225144[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2192527051590683531) {
   out_2192527051590683531[0] = 0;
   out_2192527051590683531[1] = 0;
   out_2192527051590683531[2] = 0;
   out_2192527051590683531[3] = 1;
   out_2192527051590683531[4] = 0;
   out_2192527051590683531[5] = 0;
   out_2192527051590683531[6] = 0;
   out_2192527051590683531[7] = 0;
   out_2192527051590683531[8] = 0;
   out_2192527051590683531[9] = 0;
   out_2192527051590683531[10] = 0;
   out_2192527051590683531[11] = 0;
   out_2192527051590683531[12] = 0;
   out_2192527051590683531[13] = 0;
   out_2192527051590683531[14] = 0;
   out_2192527051590683531[15] = 0;
   out_2192527051590683531[16] = 0;
   out_2192527051590683531[17] = 0;
   out_2192527051590683531[18] = 0;
   out_2192527051590683531[19] = 0;
   out_2192527051590683531[20] = 0;
   out_2192527051590683531[21] = 0;
   out_2192527051590683531[22] = 1;
   out_2192527051590683531[23] = 0;
   out_2192527051590683531[24] = 0;
   out_2192527051590683531[25] = 0;
   out_2192527051590683531[26] = 0;
   out_2192527051590683531[27] = 0;
   out_2192527051590683531[28] = 0;
   out_2192527051590683531[29] = 0;
   out_2192527051590683531[30] = 0;
   out_2192527051590683531[31] = 0;
   out_2192527051590683531[32] = 0;
   out_2192527051590683531[33] = 0;
   out_2192527051590683531[34] = 0;
   out_2192527051590683531[35] = 0;
   out_2192527051590683531[36] = 0;
   out_2192527051590683531[37] = 0;
   out_2192527051590683531[38] = 0;
   out_2192527051590683531[39] = 0;
   out_2192527051590683531[40] = 0;
   out_2192527051590683531[41] = 1;
   out_2192527051590683531[42] = 0;
   out_2192527051590683531[43] = 0;
   out_2192527051590683531[44] = 0;
   out_2192527051590683531[45] = 0;
   out_2192527051590683531[46] = 0;
   out_2192527051590683531[47] = 0;
   out_2192527051590683531[48] = 0;
   out_2192527051590683531[49] = 0;
   out_2192527051590683531[50] = 0;
   out_2192527051590683531[51] = 0;
   out_2192527051590683531[52] = 0;
   out_2192527051590683531[53] = 0;
}
void h_14(double *state, double *unused, double *out_3873502266244196496) {
   out_3873502266244196496[0] = state[6];
   out_3873502266244196496[1] = state[7];
   out_3873502266244196496[2] = state[8];
}
void H_14(double *state, double *unused, double *out_2943494082597835259) {
   out_2943494082597835259[0] = 0;
   out_2943494082597835259[1] = 0;
   out_2943494082597835259[2] = 0;
   out_2943494082597835259[3] = 0;
   out_2943494082597835259[4] = 0;
   out_2943494082597835259[5] = 0;
   out_2943494082597835259[6] = 1;
   out_2943494082597835259[7] = 0;
   out_2943494082597835259[8] = 0;
   out_2943494082597835259[9] = 0;
   out_2943494082597835259[10] = 0;
   out_2943494082597835259[11] = 0;
   out_2943494082597835259[12] = 0;
   out_2943494082597835259[13] = 0;
   out_2943494082597835259[14] = 0;
   out_2943494082597835259[15] = 0;
   out_2943494082597835259[16] = 0;
   out_2943494082597835259[17] = 0;
   out_2943494082597835259[18] = 0;
   out_2943494082597835259[19] = 0;
   out_2943494082597835259[20] = 0;
   out_2943494082597835259[21] = 0;
   out_2943494082597835259[22] = 0;
   out_2943494082597835259[23] = 0;
   out_2943494082597835259[24] = 0;
   out_2943494082597835259[25] = 1;
   out_2943494082597835259[26] = 0;
   out_2943494082597835259[27] = 0;
   out_2943494082597835259[28] = 0;
   out_2943494082597835259[29] = 0;
   out_2943494082597835259[30] = 0;
   out_2943494082597835259[31] = 0;
   out_2943494082597835259[32] = 0;
   out_2943494082597835259[33] = 0;
   out_2943494082597835259[34] = 0;
   out_2943494082597835259[35] = 0;
   out_2943494082597835259[36] = 0;
   out_2943494082597835259[37] = 0;
   out_2943494082597835259[38] = 0;
   out_2943494082597835259[39] = 0;
   out_2943494082597835259[40] = 0;
   out_2943494082597835259[41] = 0;
   out_2943494082597835259[42] = 0;
   out_2943494082597835259[43] = 0;
   out_2943494082597835259[44] = 1;
   out_2943494082597835259[45] = 0;
   out_2943494082597835259[46] = 0;
   out_2943494082597835259[47] = 0;
   out_2943494082597835259[48] = 0;
   out_2943494082597835259[49] = 0;
   out_2943494082597835259[50] = 0;
   out_2943494082597835259[51] = 0;
   out_2943494082597835259[52] = 0;
   out_2943494082597835259[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_7754318151462489406) {
  err_fun(nom_x, delta_x, out_7754318151462489406);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5172808168415891616) {
  inv_err_fun(nom_x, true_x, out_5172808168415891616);
}
void pose_H_mod_fun(double *state, double *out_2254475305049299983) {
  H_mod_fun(state, out_2254475305049299983);
}
void pose_f_fun(double *state, double dt, double *out_9187930556967356165) {
  f_fun(state,  dt, out_9187930556967356165);
}
void pose_F_fun(double *state, double dt, double *out_1250378920670806697) {
  F_fun(state,  dt, out_1250378920670806697);
}
void pose_h_4(double *state, double *unused, double *out_3431796064752050994) {
  h_4(state, unused, out_3431796064752050994);
}
void pose_H_4(double *state, double *unused, double *out_1019746773741649270) {
  H_4(state, unused, out_1019746773741649270);
}
void pose_h_10(double *state, double *unused, double *out_4742817048768310237) {
  h_10(state, unused, out_4742817048768310237);
}
void pose_H_10(double *state, double *unused, double *out_7482829619336622044) {
  H_10(state, unused, out_7482829619336622044);
}
void pose_h_13(double *state, double *unused, double *out_3124060736866225144) {
  h_13(state, unused, out_3124060736866225144);
}
void pose_H_13(double *state, double *unused, double *out_2192527051590683531) {
  H_13(state, unused, out_2192527051590683531);
}
void pose_h_14(double *state, double *unused, double *out_3873502266244196496) {
  h_14(state, unused, out_3873502266244196496);
}
void pose_H_14(double *state, double *unused, double *out_2943494082597835259) {
  H_14(state, unused, out_2943494082597835259);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
