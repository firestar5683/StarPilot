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
void err_fun(double *nom_x, double *delta_x, double *out_8810353316368700687) {
   out_8810353316368700687[0] = delta_x[0] + nom_x[0];
   out_8810353316368700687[1] = delta_x[1] + nom_x[1];
   out_8810353316368700687[2] = delta_x[2] + nom_x[2];
   out_8810353316368700687[3] = delta_x[3] + nom_x[3];
   out_8810353316368700687[4] = delta_x[4] + nom_x[4];
   out_8810353316368700687[5] = delta_x[5] + nom_x[5];
   out_8810353316368700687[6] = delta_x[6] + nom_x[6];
   out_8810353316368700687[7] = delta_x[7] + nom_x[7];
   out_8810353316368700687[8] = delta_x[8] + nom_x[8];
   out_8810353316368700687[9] = delta_x[9] + nom_x[9];
   out_8810353316368700687[10] = delta_x[10] + nom_x[10];
   out_8810353316368700687[11] = delta_x[11] + nom_x[11];
   out_8810353316368700687[12] = delta_x[12] + nom_x[12];
   out_8810353316368700687[13] = delta_x[13] + nom_x[13];
   out_8810353316368700687[14] = delta_x[14] + nom_x[14];
   out_8810353316368700687[15] = delta_x[15] + nom_x[15];
   out_8810353316368700687[16] = delta_x[16] + nom_x[16];
   out_8810353316368700687[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8282119777185922813) {
   out_8282119777185922813[0] = -nom_x[0] + true_x[0];
   out_8282119777185922813[1] = -nom_x[1] + true_x[1];
   out_8282119777185922813[2] = -nom_x[2] + true_x[2];
   out_8282119777185922813[3] = -nom_x[3] + true_x[3];
   out_8282119777185922813[4] = -nom_x[4] + true_x[4];
   out_8282119777185922813[5] = -nom_x[5] + true_x[5];
   out_8282119777185922813[6] = -nom_x[6] + true_x[6];
   out_8282119777185922813[7] = -nom_x[7] + true_x[7];
   out_8282119777185922813[8] = -nom_x[8] + true_x[8];
   out_8282119777185922813[9] = -nom_x[9] + true_x[9];
   out_8282119777185922813[10] = -nom_x[10] + true_x[10];
   out_8282119777185922813[11] = -nom_x[11] + true_x[11];
   out_8282119777185922813[12] = -nom_x[12] + true_x[12];
   out_8282119777185922813[13] = -nom_x[13] + true_x[13];
   out_8282119777185922813[14] = -nom_x[14] + true_x[14];
   out_8282119777185922813[15] = -nom_x[15] + true_x[15];
   out_8282119777185922813[16] = -nom_x[16] + true_x[16];
   out_8282119777185922813[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_9067879162073671719) {
   out_9067879162073671719[0] = 1.0;
   out_9067879162073671719[1] = 0.0;
   out_9067879162073671719[2] = 0.0;
   out_9067879162073671719[3] = 0.0;
   out_9067879162073671719[4] = 0.0;
   out_9067879162073671719[5] = 0.0;
   out_9067879162073671719[6] = 0.0;
   out_9067879162073671719[7] = 0.0;
   out_9067879162073671719[8] = 0.0;
   out_9067879162073671719[9] = 0.0;
   out_9067879162073671719[10] = 0.0;
   out_9067879162073671719[11] = 0.0;
   out_9067879162073671719[12] = 0.0;
   out_9067879162073671719[13] = 0.0;
   out_9067879162073671719[14] = 0.0;
   out_9067879162073671719[15] = 0.0;
   out_9067879162073671719[16] = 0.0;
   out_9067879162073671719[17] = 0.0;
   out_9067879162073671719[18] = 0.0;
   out_9067879162073671719[19] = 1.0;
   out_9067879162073671719[20] = 0.0;
   out_9067879162073671719[21] = 0.0;
   out_9067879162073671719[22] = 0.0;
   out_9067879162073671719[23] = 0.0;
   out_9067879162073671719[24] = 0.0;
   out_9067879162073671719[25] = 0.0;
   out_9067879162073671719[26] = 0.0;
   out_9067879162073671719[27] = 0.0;
   out_9067879162073671719[28] = 0.0;
   out_9067879162073671719[29] = 0.0;
   out_9067879162073671719[30] = 0.0;
   out_9067879162073671719[31] = 0.0;
   out_9067879162073671719[32] = 0.0;
   out_9067879162073671719[33] = 0.0;
   out_9067879162073671719[34] = 0.0;
   out_9067879162073671719[35] = 0.0;
   out_9067879162073671719[36] = 0.0;
   out_9067879162073671719[37] = 0.0;
   out_9067879162073671719[38] = 1.0;
   out_9067879162073671719[39] = 0.0;
   out_9067879162073671719[40] = 0.0;
   out_9067879162073671719[41] = 0.0;
   out_9067879162073671719[42] = 0.0;
   out_9067879162073671719[43] = 0.0;
   out_9067879162073671719[44] = 0.0;
   out_9067879162073671719[45] = 0.0;
   out_9067879162073671719[46] = 0.0;
   out_9067879162073671719[47] = 0.0;
   out_9067879162073671719[48] = 0.0;
   out_9067879162073671719[49] = 0.0;
   out_9067879162073671719[50] = 0.0;
   out_9067879162073671719[51] = 0.0;
   out_9067879162073671719[52] = 0.0;
   out_9067879162073671719[53] = 0.0;
   out_9067879162073671719[54] = 0.0;
   out_9067879162073671719[55] = 0.0;
   out_9067879162073671719[56] = 0.0;
   out_9067879162073671719[57] = 1.0;
   out_9067879162073671719[58] = 0.0;
   out_9067879162073671719[59] = 0.0;
   out_9067879162073671719[60] = 0.0;
   out_9067879162073671719[61] = 0.0;
   out_9067879162073671719[62] = 0.0;
   out_9067879162073671719[63] = 0.0;
   out_9067879162073671719[64] = 0.0;
   out_9067879162073671719[65] = 0.0;
   out_9067879162073671719[66] = 0.0;
   out_9067879162073671719[67] = 0.0;
   out_9067879162073671719[68] = 0.0;
   out_9067879162073671719[69] = 0.0;
   out_9067879162073671719[70] = 0.0;
   out_9067879162073671719[71] = 0.0;
   out_9067879162073671719[72] = 0.0;
   out_9067879162073671719[73] = 0.0;
   out_9067879162073671719[74] = 0.0;
   out_9067879162073671719[75] = 0.0;
   out_9067879162073671719[76] = 1.0;
   out_9067879162073671719[77] = 0.0;
   out_9067879162073671719[78] = 0.0;
   out_9067879162073671719[79] = 0.0;
   out_9067879162073671719[80] = 0.0;
   out_9067879162073671719[81] = 0.0;
   out_9067879162073671719[82] = 0.0;
   out_9067879162073671719[83] = 0.0;
   out_9067879162073671719[84] = 0.0;
   out_9067879162073671719[85] = 0.0;
   out_9067879162073671719[86] = 0.0;
   out_9067879162073671719[87] = 0.0;
   out_9067879162073671719[88] = 0.0;
   out_9067879162073671719[89] = 0.0;
   out_9067879162073671719[90] = 0.0;
   out_9067879162073671719[91] = 0.0;
   out_9067879162073671719[92] = 0.0;
   out_9067879162073671719[93] = 0.0;
   out_9067879162073671719[94] = 0.0;
   out_9067879162073671719[95] = 1.0;
   out_9067879162073671719[96] = 0.0;
   out_9067879162073671719[97] = 0.0;
   out_9067879162073671719[98] = 0.0;
   out_9067879162073671719[99] = 0.0;
   out_9067879162073671719[100] = 0.0;
   out_9067879162073671719[101] = 0.0;
   out_9067879162073671719[102] = 0.0;
   out_9067879162073671719[103] = 0.0;
   out_9067879162073671719[104] = 0.0;
   out_9067879162073671719[105] = 0.0;
   out_9067879162073671719[106] = 0.0;
   out_9067879162073671719[107] = 0.0;
   out_9067879162073671719[108] = 0.0;
   out_9067879162073671719[109] = 0.0;
   out_9067879162073671719[110] = 0.0;
   out_9067879162073671719[111] = 0.0;
   out_9067879162073671719[112] = 0.0;
   out_9067879162073671719[113] = 0.0;
   out_9067879162073671719[114] = 1.0;
   out_9067879162073671719[115] = 0.0;
   out_9067879162073671719[116] = 0.0;
   out_9067879162073671719[117] = 0.0;
   out_9067879162073671719[118] = 0.0;
   out_9067879162073671719[119] = 0.0;
   out_9067879162073671719[120] = 0.0;
   out_9067879162073671719[121] = 0.0;
   out_9067879162073671719[122] = 0.0;
   out_9067879162073671719[123] = 0.0;
   out_9067879162073671719[124] = 0.0;
   out_9067879162073671719[125] = 0.0;
   out_9067879162073671719[126] = 0.0;
   out_9067879162073671719[127] = 0.0;
   out_9067879162073671719[128] = 0.0;
   out_9067879162073671719[129] = 0.0;
   out_9067879162073671719[130] = 0.0;
   out_9067879162073671719[131] = 0.0;
   out_9067879162073671719[132] = 0.0;
   out_9067879162073671719[133] = 1.0;
   out_9067879162073671719[134] = 0.0;
   out_9067879162073671719[135] = 0.0;
   out_9067879162073671719[136] = 0.0;
   out_9067879162073671719[137] = 0.0;
   out_9067879162073671719[138] = 0.0;
   out_9067879162073671719[139] = 0.0;
   out_9067879162073671719[140] = 0.0;
   out_9067879162073671719[141] = 0.0;
   out_9067879162073671719[142] = 0.0;
   out_9067879162073671719[143] = 0.0;
   out_9067879162073671719[144] = 0.0;
   out_9067879162073671719[145] = 0.0;
   out_9067879162073671719[146] = 0.0;
   out_9067879162073671719[147] = 0.0;
   out_9067879162073671719[148] = 0.0;
   out_9067879162073671719[149] = 0.0;
   out_9067879162073671719[150] = 0.0;
   out_9067879162073671719[151] = 0.0;
   out_9067879162073671719[152] = 1.0;
   out_9067879162073671719[153] = 0.0;
   out_9067879162073671719[154] = 0.0;
   out_9067879162073671719[155] = 0.0;
   out_9067879162073671719[156] = 0.0;
   out_9067879162073671719[157] = 0.0;
   out_9067879162073671719[158] = 0.0;
   out_9067879162073671719[159] = 0.0;
   out_9067879162073671719[160] = 0.0;
   out_9067879162073671719[161] = 0.0;
   out_9067879162073671719[162] = 0.0;
   out_9067879162073671719[163] = 0.0;
   out_9067879162073671719[164] = 0.0;
   out_9067879162073671719[165] = 0.0;
   out_9067879162073671719[166] = 0.0;
   out_9067879162073671719[167] = 0.0;
   out_9067879162073671719[168] = 0.0;
   out_9067879162073671719[169] = 0.0;
   out_9067879162073671719[170] = 0.0;
   out_9067879162073671719[171] = 1.0;
   out_9067879162073671719[172] = 0.0;
   out_9067879162073671719[173] = 0.0;
   out_9067879162073671719[174] = 0.0;
   out_9067879162073671719[175] = 0.0;
   out_9067879162073671719[176] = 0.0;
   out_9067879162073671719[177] = 0.0;
   out_9067879162073671719[178] = 0.0;
   out_9067879162073671719[179] = 0.0;
   out_9067879162073671719[180] = 0.0;
   out_9067879162073671719[181] = 0.0;
   out_9067879162073671719[182] = 0.0;
   out_9067879162073671719[183] = 0.0;
   out_9067879162073671719[184] = 0.0;
   out_9067879162073671719[185] = 0.0;
   out_9067879162073671719[186] = 0.0;
   out_9067879162073671719[187] = 0.0;
   out_9067879162073671719[188] = 0.0;
   out_9067879162073671719[189] = 0.0;
   out_9067879162073671719[190] = 1.0;
   out_9067879162073671719[191] = 0.0;
   out_9067879162073671719[192] = 0.0;
   out_9067879162073671719[193] = 0.0;
   out_9067879162073671719[194] = 0.0;
   out_9067879162073671719[195] = 0.0;
   out_9067879162073671719[196] = 0.0;
   out_9067879162073671719[197] = 0.0;
   out_9067879162073671719[198] = 0.0;
   out_9067879162073671719[199] = 0.0;
   out_9067879162073671719[200] = 0.0;
   out_9067879162073671719[201] = 0.0;
   out_9067879162073671719[202] = 0.0;
   out_9067879162073671719[203] = 0.0;
   out_9067879162073671719[204] = 0.0;
   out_9067879162073671719[205] = 0.0;
   out_9067879162073671719[206] = 0.0;
   out_9067879162073671719[207] = 0.0;
   out_9067879162073671719[208] = 0.0;
   out_9067879162073671719[209] = 1.0;
   out_9067879162073671719[210] = 0.0;
   out_9067879162073671719[211] = 0.0;
   out_9067879162073671719[212] = 0.0;
   out_9067879162073671719[213] = 0.0;
   out_9067879162073671719[214] = 0.0;
   out_9067879162073671719[215] = 0.0;
   out_9067879162073671719[216] = 0.0;
   out_9067879162073671719[217] = 0.0;
   out_9067879162073671719[218] = 0.0;
   out_9067879162073671719[219] = 0.0;
   out_9067879162073671719[220] = 0.0;
   out_9067879162073671719[221] = 0.0;
   out_9067879162073671719[222] = 0.0;
   out_9067879162073671719[223] = 0.0;
   out_9067879162073671719[224] = 0.0;
   out_9067879162073671719[225] = 0.0;
   out_9067879162073671719[226] = 0.0;
   out_9067879162073671719[227] = 0.0;
   out_9067879162073671719[228] = 1.0;
   out_9067879162073671719[229] = 0.0;
   out_9067879162073671719[230] = 0.0;
   out_9067879162073671719[231] = 0.0;
   out_9067879162073671719[232] = 0.0;
   out_9067879162073671719[233] = 0.0;
   out_9067879162073671719[234] = 0.0;
   out_9067879162073671719[235] = 0.0;
   out_9067879162073671719[236] = 0.0;
   out_9067879162073671719[237] = 0.0;
   out_9067879162073671719[238] = 0.0;
   out_9067879162073671719[239] = 0.0;
   out_9067879162073671719[240] = 0.0;
   out_9067879162073671719[241] = 0.0;
   out_9067879162073671719[242] = 0.0;
   out_9067879162073671719[243] = 0.0;
   out_9067879162073671719[244] = 0.0;
   out_9067879162073671719[245] = 0.0;
   out_9067879162073671719[246] = 0.0;
   out_9067879162073671719[247] = 1.0;
   out_9067879162073671719[248] = 0.0;
   out_9067879162073671719[249] = 0.0;
   out_9067879162073671719[250] = 0.0;
   out_9067879162073671719[251] = 0.0;
   out_9067879162073671719[252] = 0.0;
   out_9067879162073671719[253] = 0.0;
   out_9067879162073671719[254] = 0.0;
   out_9067879162073671719[255] = 0.0;
   out_9067879162073671719[256] = 0.0;
   out_9067879162073671719[257] = 0.0;
   out_9067879162073671719[258] = 0.0;
   out_9067879162073671719[259] = 0.0;
   out_9067879162073671719[260] = 0.0;
   out_9067879162073671719[261] = 0.0;
   out_9067879162073671719[262] = 0.0;
   out_9067879162073671719[263] = 0.0;
   out_9067879162073671719[264] = 0.0;
   out_9067879162073671719[265] = 0.0;
   out_9067879162073671719[266] = 1.0;
   out_9067879162073671719[267] = 0.0;
   out_9067879162073671719[268] = 0.0;
   out_9067879162073671719[269] = 0.0;
   out_9067879162073671719[270] = 0.0;
   out_9067879162073671719[271] = 0.0;
   out_9067879162073671719[272] = 0.0;
   out_9067879162073671719[273] = 0.0;
   out_9067879162073671719[274] = 0.0;
   out_9067879162073671719[275] = 0.0;
   out_9067879162073671719[276] = 0.0;
   out_9067879162073671719[277] = 0.0;
   out_9067879162073671719[278] = 0.0;
   out_9067879162073671719[279] = 0.0;
   out_9067879162073671719[280] = 0.0;
   out_9067879162073671719[281] = 0.0;
   out_9067879162073671719[282] = 0.0;
   out_9067879162073671719[283] = 0.0;
   out_9067879162073671719[284] = 0.0;
   out_9067879162073671719[285] = 1.0;
   out_9067879162073671719[286] = 0.0;
   out_9067879162073671719[287] = 0.0;
   out_9067879162073671719[288] = 0.0;
   out_9067879162073671719[289] = 0.0;
   out_9067879162073671719[290] = 0.0;
   out_9067879162073671719[291] = 0.0;
   out_9067879162073671719[292] = 0.0;
   out_9067879162073671719[293] = 0.0;
   out_9067879162073671719[294] = 0.0;
   out_9067879162073671719[295] = 0.0;
   out_9067879162073671719[296] = 0.0;
   out_9067879162073671719[297] = 0.0;
   out_9067879162073671719[298] = 0.0;
   out_9067879162073671719[299] = 0.0;
   out_9067879162073671719[300] = 0.0;
   out_9067879162073671719[301] = 0.0;
   out_9067879162073671719[302] = 0.0;
   out_9067879162073671719[303] = 0.0;
   out_9067879162073671719[304] = 1.0;
   out_9067879162073671719[305] = 0.0;
   out_9067879162073671719[306] = 0.0;
   out_9067879162073671719[307] = 0.0;
   out_9067879162073671719[308] = 0.0;
   out_9067879162073671719[309] = 0.0;
   out_9067879162073671719[310] = 0.0;
   out_9067879162073671719[311] = 0.0;
   out_9067879162073671719[312] = 0.0;
   out_9067879162073671719[313] = 0.0;
   out_9067879162073671719[314] = 0.0;
   out_9067879162073671719[315] = 0.0;
   out_9067879162073671719[316] = 0.0;
   out_9067879162073671719[317] = 0.0;
   out_9067879162073671719[318] = 0.0;
   out_9067879162073671719[319] = 0.0;
   out_9067879162073671719[320] = 0.0;
   out_9067879162073671719[321] = 0.0;
   out_9067879162073671719[322] = 0.0;
   out_9067879162073671719[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6384990450931193177) {
   out_6384990450931193177[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6384990450931193177[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6384990450931193177[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6384990450931193177[3] = dt*state[12] + state[3];
   out_6384990450931193177[4] = dt*state[13] + state[4];
   out_6384990450931193177[5] = dt*state[14] + state[5];
   out_6384990450931193177[6] = state[6];
   out_6384990450931193177[7] = state[7];
   out_6384990450931193177[8] = state[8];
   out_6384990450931193177[9] = state[9];
   out_6384990450931193177[10] = state[10];
   out_6384990450931193177[11] = state[11];
   out_6384990450931193177[12] = state[12];
   out_6384990450931193177[13] = state[13];
   out_6384990450931193177[14] = state[14];
   out_6384990450931193177[15] = state[15];
   out_6384990450931193177[16] = state[16];
   out_6384990450931193177[17] = state[17];
}
void F_fun(double *state, double dt, double *out_105498423206002474) {
   out_105498423206002474[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_105498423206002474[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_105498423206002474[2] = 0;
   out_105498423206002474[3] = 0;
   out_105498423206002474[4] = 0;
   out_105498423206002474[5] = 0;
   out_105498423206002474[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_105498423206002474[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_105498423206002474[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_105498423206002474[9] = 0;
   out_105498423206002474[10] = 0;
   out_105498423206002474[11] = 0;
   out_105498423206002474[12] = 0;
   out_105498423206002474[13] = 0;
   out_105498423206002474[14] = 0;
   out_105498423206002474[15] = 0;
   out_105498423206002474[16] = 0;
   out_105498423206002474[17] = 0;
   out_105498423206002474[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_105498423206002474[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_105498423206002474[20] = 0;
   out_105498423206002474[21] = 0;
   out_105498423206002474[22] = 0;
   out_105498423206002474[23] = 0;
   out_105498423206002474[24] = 0;
   out_105498423206002474[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_105498423206002474[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_105498423206002474[27] = 0;
   out_105498423206002474[28] = 0;
   out_105498423206002474[29] = 0;
   out_105498423206002474[30] = 0;
   out_105498423206002474[31] = 0;
   out_105498423206002474[32] = 0;
   out_105498423206002474[33] = 0;
   out_105498423206002474[34] = 0;
   out_105498423206002474[35] = 0;
   out_105498423206002474[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_105498423206002474[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_105498423206002474[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_105498423206002474[39] = 0;
   out_105498423206002474[40] = 0;
   out_105498423206002474[41] = 0;
   out_105498423206002474[42] = 0;
   out_105498423206002474[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_105498423206002474[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_105498423206002474[45] = 0;
   out_105498423206002474[46] = 0;
   out_105498423206002474[47] = 0;
   out_105498423206002474[48] = 0;
   out_105498423206002474[49] = 0;
   out_105498423206002474[50] = 0;
   out_105498423206002474[51] = 0;
   out_105498423206002474[52] = 0;
   out_105498423206002474[53] = 0;
   out_105498423206002474[54] = 0;
   out_105498423206002474[55] = 0;
   out_105498423206002474[56] = 0;
   out_105498423206002474[57] = 1;
   out_105498423206002474[58] = 0;
   out_105498423206002474[59] = 0;
   out_105498423206002474[60] = 0;
   out_105498423206002474[61] = 0;
   out_105498423206002474[62] = 0;
   out_105498423206002474[63] = 0;
   out_105498423206002474[64] = 0;
   out_105498423206002474[65] = 0;
   out_105498423206002474[66] = dt;
   out_105498423206002474[67] = 0;
   out_105498423206002474[68] = 0;
   out_105498423206002474[69] = 0;
   out_105498423206002474[70] = 0;
   out_105498423206002474[71] = 0;
   out_105498423206002474[72] = 0;
   out_105498423206002474[73] = 0;
   out_105498423206002474[74] = 0;
   out_105498423206002474[75] = 0;
   out_105498423206002474[76] = 1;
   out_105498423206002474[77] = 0;
   out_105498423206002474[78] = 0;
   out_105498423206002474[79] = 0;
   out_105498423206002474[80] = 0;
   out_105498423206002474[81] = 0;
   out_105498423206002474[82] = 0;
   out_105498423206002474[83] = 0;
   out_105498423206002474[84] = 0;
   out_105498423206002474[85] = dt;
   out_105498423206002474[86] = 0;
   out_105498423206002474[87] = 0;
   out_105498423206002474[88] = 0;
   out_105498423206002474[89] = 0;
   out_105498423206002474[90] = 0;
   out_105498423206002474[91] = 0;
   out_105498423206002474[92] = 0;
   out_105498423206002474[93] = 0;
   out_105498423206002474[94] = 0;
   out_105498423206002474[95] = 1;
   out_105498423206002474[96] = 0;
   out_105498423206002474[97] = 0;
   out_105498423206002474[98] = 0;
   out_105498423206002474[99] = 0;
   out_105498423206002474[100] = 0;
   out_105498423206002474[101] = 0;
   out_105498423206002474[102] = 0;
   out_105498423206002474[103] = 0;
   out_105498423206002474[104] = dt;
   out_105498423206002474[105] = 0;
   out_105498423206002474[106] = 0;
   out_105498423206002474[107] = 0;
   out_105498423206002474[108] = 0;
   out_105498423206002474[109] = 0;
   out_105498423206002474[110] = 0;
   out_105498423206002474[111] = 0;
   out_105498423206002474[112] = 0;
   out_105498423206002474[113] = 0;
   out_105498423206002474[114] = 1;
   out_105498423206002474[115] = 0;
   out_105498423206002474[116] = 0;
   out_105498423206002474[117] = 0;
   out_105498423206002474[118] = 0;
   out_105498423206002474[119] = 0;
   out_105498423206002474[120] = 0;
   out_105498423206002474[121] = 0;
   out_105498423206002474[122] = 0;
   out_105498423206002474[123] = 0;
   out_105498423206002474[124] = 0;
   out_105498423206002474[125] = 0;
   out_105498423206002474[126] = 0;
   out_105498423206002474[127] = 0;
   out_105498423206002474[128] = 0;
   out_105498423206002474[129] = 0;
   out_105498423206002474[130] = 0;
   out_105498423206002474[131] = 0;
   out_105498423206002474[132] = 0;
   out_105498423206002474[133] = 1;
   out_105498423206002474[134] = 0;
   out_105498423206002474[135] = 0;
   out_105498423206002474[136] = 0;
   out_105498423206002474[137] = 0;
   out_105498423206002474[138] = 0;
   out_105498423206002474[139] = 0;
   out_105498423206002474[140] = 0;
   out_105498423206002474[141] = 0;
   out_105498423206002474[142] = 0;
   out_105498423206002474[143] = 0;
   out_105498423206002474[144] = 0;
   out_105498423206002474[145] = 0;
   out_105498423206002474[146] = 0;
   out_105498423206002474[147] = 0;
   out_105498423206002474[148] = 0;
   out_105498423206002474[149] = 0;
   out_105498423206002474[150] = 0;
   out_105498423206002474[151] = 0;
   out_105498423206002474[152] = 1;
   out_105498423206002474[153] = 0;
   out_105498423206002474[154] = 0;
   out_105498423206002474[155] = 0;
   out_105498423206002474[156] = 0;
   out_105498423206002474[157] = 0;
   out_105498423206002474[158] = 0;
   out_105498423206002474[159] = 0;
   out_105498423206002474[160] = 0;
   out_105498423206002474[161] = 0;
   out_105498423206002474[162] = 0;
   out_105498423206002474[163] = 0;
   out_105498423206002474[164] = 0;
   out_105498423206002474[165] = 0;
   out_105498423206002474[166] = 0;
   out_105498423206002474[167] = 0;
   out_105498423206002474[168] = 0;
   out_105498423206002474[169] = 0;
   out_105498423206002474[170] = 0;
   out_105498423206002474[171] = 1;
   out_105498423206002474[172] = 0;
   out_105498423206002474[173] = 0;
   out_105498423206002474[174] = 0;
   out_105498423206002474[175] = 0;
   out_105498423206002474[176] = 0;
   out_105498423206002474[177] = 0;
   out_105498423206002474[178] = 0;
   out_105498423206002474[179] = 0;
   out_105498423206002474[180] = 0;
   out_105498423206002474[181] = 0;
   out_105498423206002474[182] = 0;
   out_105498423206002474[183] = 0;
   out_105498423206002474[184] = 0;
   out_105498423206002474[185] = 0;
   out_105498423206002474[186] = 0;
   out_105498423206002474[187] = 0;
   out_105498423206002474[188] = 0;
   out_105498423206002474[189] = 0;
   out_105498423206002474[190] = 1;
   out_105498423206002474[191] = 0;
   out_105498423206002474[192] = 0;
   out_105498423206002474[193] = 0;
   out_105498423206002474[194] = 0;
   out_105498423206002474[195] = 0;
   out_105498423206002474[196] = 0;
   out_105498423206002474[197] = 0;
   out_105498423206002474[198] = 0;
   out_105498423206002474[199] = 0;
   out_105498423206002474[200] = 0;
   out_105498423206002474[201] = 0;
   out_105498423206002474[202] = 0;
   out_105498423206002474[203] = 0;
   out_105498423206002474[204] = 0;
   out_105498423206002474[205] = 0;
   out_105498423206002474[206] = 0;
   out_105498423206002474[207] = 0;
   out_105498423206002474[208] = 0;
   out_105498423206002474[209] = 1;
   out_105498423206002474[210] = 0;
   out_105498423206002474[211] = 0;
   out_105498423206002474[212] = 0;
   out_105498423206002474[213] = 0;
   out_105498423206002474[214] = 0;
   out_105498423206002474[215] = 0;
   out_105498423206002474[216] = 0;
   out_105498423206002474[217] = 0;
   out_105498423206002474[218] = 0;
   out_105498423206002474[219] = 0;
   out_105498423206002474[220] = 0;
   out_105498423206002474[221] = 0;
   out_105498423206002474[222] = 0;
   out_105498423206002474[223] = 0;
   out_105498423206002474[224] = 0;
   out_105498423206002474[225] = 0;
   out_105498423206002474[226] = 0;
   out_105498423206002474[227] = 0;
   out_105498423206002474[228] = 1;
   out_105498423206002474[229] = 0;
   out_105498423206002474[230] = 0;
   out_105498423206002474[231] = 0;
   out_105498423206002474[232] = 0;
   out_105498423206002474[233] = 0;
   out_105498423206002474[234] = 0;
   out_105498423206002474[235] = 0;
   out_105498423206002474[236] = 0;
   out_105498423206002474[237] = 0;
   out_105498423206002474[238] = 0;
   out_105498423206002474[239] = 0;
   out_105498423206002474[240] = 0;
   out_105498423206002474[241] = 0;
   out_105498423206002474[242] = 0;
   out_105498423206002474[243] = 0;
   out_105498423206002474[244] = 0;
   out_105498423206002474[245] = 0;
   out_105498423206002474[246] = 0;
   out_105498423206002474[247] = 1;
   out_105498423206002474[248] = 0;
   out_105498423206002474[249] = 0;
   out_105498423206002474[250] = 0;
   out_105498423206002474[251] = 0;
   out_105498423206002474[252] = 0;
   out_105498423206002474[253] = 0;
   out_105498423206002474[254] = 0;
   out_105498423206002474[255] = 0;
   out_105498423206002474[256] = 0;
   out_105498423206002474[257] = 0;
   out_105498423206002474[258] = 0;
   out_105498423206002474[259] = 0;
   out_105498423206002474[260] = 0;
   out_105498423206002474[261] = 0;
   out_105498423206002474[262] = 0;
   out_105498423206002474[263] = 0;
   out_105498423206002474[264] = 0;
   out_105498423206002474[265] = 0;
   out_105498423206002474[266] = 1;
   out_105498423206002474[267] = 0;
   out_105498423206002474[268] = 0;
   out_105498423206002474[269] = 0;
   out_105498423206002474[270] = 0;
   out_105498423206002474[271] = 0;
   out_105498423206002474[272] = 0;
   out_105498423206002474[273] = 0;
   out_105498423206002474[274] = 0;
   out_105498423206002474[275] = 0;
   out_105498423206002474[276] = 0;
   out_105498423206002474[277] = 0;
   out_105498423206002474[278] = 0;
   out_105498423206002474[279] = 0;
   out_105498423206002474[280] = 0;
   out_105498423206002474[281] = 0;
   out_105498423206002474[282] = 0;
   out_105498423206002474[283] = 0;
   out_105498423206002474[284] = 0;
   out_105498423206002474[285] = 1;
   out_105498423206002474[286] = 0;
   out_105498423206002474[287] = 0;
   out_105498423206002474[288] = 0;
   out_105498423206002474[289] = 0;
   out_105498423206002474[290] = 0;
   out_105498423206002474[291] = 0;
   out_105498423206002474[292] = 0;
   out_105498423206002474[293] = 0;
   out_105498423206002474[294] = 0;
   out_105498423206002474[295] = 0;
   out_105498423206002474[296] = 0;
   out_105498423206002474[297] = 0;
   out_105498423206002474[298] = 0;
   out_105498423206002474[299] = 0;
   out_105498423206002474[300] = 0;
   out_105498423206002474[301] = 0;
   out_105498423206002474[302] = 0;
   out_105498423206002474[303] = 0;
   out_105498423206002474[304] = 1;
   out_105498423206002474[305] = 0;
   out_105498423206002474[306] = 0;
   out_105498423206002474[307] = 0;
   out_105498423206002474[308] = 0;
   out_105498423206002474[309] = 0;
   out_105498423206002474[310] = 0;
   out_105498423206002474[311] = 0;
   out_105498423206002474[312] = 0;
   out_105498423206002474[313] = 0;
   out_105498423206002474[314] = 0;
   out_105498423206002474[315] = 0;
   out_105498423206002474[316] = 0;
   out_105498423206002474[317] = 0;
   out_105498423206002474[318] = 0;
   out_105498423206002474[319] = 0;
   out_105498423206002474[320] = 0;
   out_105498423206002474[321] = 0;
   out_105498423206002474[322] = 0;
   out_105498423206002474[323] = 1;
}
void h_4(double *state, double *unused, double *out_3142206333536839736) {
   out_3142206333536839736[0] = state[6] + state[9];
   out_3142206333536839736[1] = state[7] + state[10];
   out_3142206333536839736[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_123517496015850377) {
   out_123517496015850377[0] = 0;
   out_123517496015850377[1] = 0;
   out_123517496015850377[2] = 0;
   out_123517496015850377[3] = 0;
   out_123517496015850377[4] = 0;
   out_123517496015850377[5] = 0;
   out_123517496015850377[6] = 1;
   out_123517496015850377[7] = 0;
   out_123517496015850377[8] = 0;
   out_123517496015850377[9] = 1;
   out_123517496015850377[10] = 0;
   out_123517496015850377[11] = 0;
   out_123517496015850377[12] = 0;
   out_123517496015850377[13] = 0;
   out_123517496015850377[14] = 0;
   out_123517496015850377[15] = 0;
   out_123517496015850377[16] = 0;
   out_123517496015850377[17] = 0;
   out_123517496015850377[18] = 0;
   out_123517496015850377[19] = 0;
   out_123517496015850377[20] = 0;
   out_123517496015850377[21] = 0;
   out_123517496015850377[22] = 0;
   out_123517496015850377[23] = 0;
   out_123517496015850377[24] = 0;
   out_123517496015850377[25] = 1;
   out_123517496015850377[26] = 0;
   out_123517496015850377[27] = 0;
   out_123517496015850377[28] = 1;
   out_123517496015850377[29] = 0;
   out_123517496015850377[30] = 0;
   out_123517496015850377[31] = 0;
   out_123517496015850377[32] = 0;
   out_123517496015850377[33] = 0;
   out_123517496015850377[34] = 0;
   out_123517496015850377[35] = 0;
   out_123517496015850377[36] = 0;
   out_123517496015850377[37] = 0;
   out_123517496015850377[38] = 0;
   out_123517496015850377[39] = 0;
   out_123517496015850377[40] = 0;
   out_123517496015850377[41] = 0;
   out_123517496015850377[42] = 0;
   out_123517496015850377[43] = 0;
   out_123517496015850377[44] = 1;
   out_123517496015850377[45] = 0;
   out_123517496015850377[46] = 0;
   out_123517496015850377[47] = 1;
   out_123517496015850377[48] = 0;
   out_123517496015850377[49] = 0;
   out_123517496015850377[50] = 0;
   out_123517496015850377[51] = 0;
   out_123517496015850377[52] = 0;
   out_123517496015850377[53] = 0;
}
void h_10(double *state, double *unused, double *out_7019642631864442983) {
   out_7019642631864442983[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7019642631864442983[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7019642631864442983[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8619357166475704864) {
   out_8619357166475704864[0] = 0;
   out_8619357166475704864[1] = 9.8100000000000005*cos(state[1]);
   out_8619357166475704864[2] = 0;
   out_8619357166475704864[3] = 0;
   out_8619357166475704864[4] = -state[8];
   out_8619357166475704864[5] = state[7];
   out_8619357166475704864[6] = 0;
   out_8619357166475704864[7] = state[5];
   out_8619357166475704864[8] = -state[4];
   out_8619357166475704864[9] = 0;
   out_8619357166475704864[10] = 0;
   out_8619357166475704864[11] = 0;
   out_8619357166475704864[12] = 1;
   out_8619357166475704864[13] = 0;
   out_8619357166475704864[14] = 0;
   out_8619357166475704864[15] = 1;
   out_8619357166475704864[16] = 0;
   out_8619357166475704864[17] = 0;
   out_8619357166475704864[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8619357166475704864[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8619357166475704864[20] = 0;
   out_8619357166475704864[21] = state[8];
   out_8619357166475704864[22] = 0;
   out_8619357166475704864[23] = -state[6];
   out_8619357166475704864[24] = -state[5];
   out_8619357166475704864[25] = 0;
   out_8619357166475704864[26] = state[3];
   out_8619357166475704864[27] = 0;
   out_8619357166475704864[28] = 0;
   out_8619357166475704864[29] = 0;
   out_8619357166475704864[30] = 0;
   out_8619357166475704864[31] = 1;
   out_8619357166475704864[32] = 0;
   out_8619357166475704864[33] = 0;
   out_8619357166475704864[34] = 1;
   out_8619357166475704864[35] = 0;
   out_8619357166475704864[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8619357166475704864[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8619357166475704864[38] = 0;
   out_8619357166475704864[39] = -state[7];
   out_8619357166475704864[40] = state[6];
   out_8619357166475704864[41] = 0;
   out_8619357166475704864[42] = state[4];
   out_8619357166475704864[43] = -state[3];
   out_8619357166475704864[44] = 0;
   out_8619357166475704864[45] = 0;
   out_8619357166475704864[46] = 0;
   out_8619357166475704864[47] = 0;
   out_8619357166475704864[48] = 0;
   out_8619357166475704864[49] = 0;
   out_8619357166475704864[50] = 1;
   out_8619357166475704864[51] = 0;
   out_8619357166475704864[52] = 0;
   out_8619357166475704864[53] = 1;
}
void h_13(double *state, double *unused, double *out_7946660746268207299) {
   out_7946660746268207299[0] = state[3];
   out_7946660746268207299[1] = state[4];
   out_7946660746268207299[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3710237967286673647) {
   out_3710237967286673647[0] = 0;
   out_3710237967286673647[1] = 0;
   out_3710237967286673647[2] = 0;
   out_3710237967286673647[3] = 1;
   out_3710237967286673647[4] = 0;
   out_3710237967286673647[5] = 0;
   out_3710237967286673647[6] = 0;
   out_3710237967286673647[7] = 0;
   out_3710237967286673647[8] = 0;
   out_3710237967286673647[9] = 0;
   out_3710237967286673647[10] = 0;
   out_3710237967286673647[11] = 0;
   out_3710237967286673647[12] = 0;
   out_3710237967286673647[13] = 0;
   out_3710237967286673647[14] = 0;
   out_3710237967286673647[15] = 0;
   out_3710237967286673647[16] = 0;
   out_3710237967286673647[17] = 0;
   out_3710237967286673647[18] = 0;
   out_3710237967286673647[19] = 0;
   out_3710237967286673647[20] = 0;
   out_3710237967286673647[21] = 0;
   out_3710237967286673647[22] = 1;
   out_3710237967286673647[23] = 0;
   out_3710237967286673647[24] = 0;
   out_3710237967286673647[25] = 0;
   out_3710237967286673647[26] = 0;
   out_3710237967286673647[27] = 0;
   out_3710237967286673647[28] = 0;
   out_3710237967286673647[29] = 0;
   out_3710237967286673647[30] = 0;
   out_3710237967286673647[31] = 0;
   out_3710237967286673647[32] = 0;
   out_3710237967286673647[33] = 0;
   out_3710237967286673647[34] = 0;
   out_3710237967286673647[35] = 0;
   out_3710237967286673647[36] = 0;
   out_3710237967286673647[37] = 0;
   out_3710237967286673647[38] = 0;
   out_3710237967286673647[39] = 0;
   out_3710237967286673647[40] = 0;
   out_3710237967286673647[41] = 1;
   out_3710237967286673647[42] = 0;
   out_3710237967286673647[43] = 0;
   out_3710237967286673647[44] = 0;
   out_3710237967286673647[45] = 0;
   out_3710237967286673647[46] = 0;
   out_3710237967286673647[47] = 0;
   out_3710237967286673647[48] = 0;
   out_3710237967286673647[49] = 0;
   out_3710237967286673647[50] = 0;
   out_3710237967286673647[51] = 0;
   out_3710237967286673647[52] = 0;
   out_3710237967286673647[53] = 0;
}
void h_14(double *state, double *unused, double *out_6202390496101391785) {
   out_6202390496101391785[0] = state[6];
   out_6202390496101391785[1] = state[7];
   out_6202390496101391785[2] = state[8];
}
void H_14(double *state, double *unused, double *out_2959270936279521919) {
   out_2959270936279521919[0] = 0;
   out_2959270936279521919[1] = 0;
   out_2959270936279521919[2] = 0;
   out_2959270936279521919[3] = 0;
   out_2959270936279521919[4] = 0;
   out_2959270936279521919[5] = 0;
   out_2959270936279521919[6] = 1;
   out_2959270936279521919[7] = 0;
   out_2959270936279521919[8] = 0;
   out_2959270936279521919[9] = 0;
   out_2959270936279521919[10] = 0;
   out_2959270936279521919[11] = 0;
   out_2959270936279521919[12] = 0;
   out_2959270936279521919[13] = 0;
   out_2959270936279521919[14] = 0;
   out_2959270936279521919[15] = 0;
   out_2959270936279521919[16] = 0;
   out_2959270936279521919[17] = 0;
   out_2959270936279521919[18] = 0;
   out_2959270936279521919[19] = 0;
   out_2959270936279521919[20] = 0;
   out_2959270936279521919[21] = 0;
   out_2959270936279521919[22] = 0;
   out_2959270936279521919[23] = 0;
   out_2959270936279521919[24] = 0;
   out_2959270936279521919[25] = 1;
   out_2959270936279521919[26] = 0;
   out_2959270936279521919[27] = 0;
   out_2959270936279521919[28] = 0;
   out_2959270936279521919[29] = 0;
   out_2959270936279521919[30] = 0;
   out_2959270936279521919[31] = 0;
   out_2959270936279521919[32] = 0;
   out_2959270936279521919[33] = 0;
   out_2959270936279521919[34] = 0;
   out_2959270936279521919[35] = 0;
   out_2959270936279521919[36] = 0;
   out_2959270936279521919[37] = 0;
   out_2959270936279521919[38] = 0;
   out_2959270936279521919[39] = 0;
   out_2959270936279521919[40] = 0;
   out_2959270936279521919[41] = 0;
   out_2959270936279521919[42] = 0;
   out_2959270936279521919[43] = 0;
   out_2959270936279521919[44] = 1;
   out_2959270936279521919[45] = 0;
   out_2959270936279521919[46] = 0;
   out_2959270936279521919[47] = 0;
   out_2959270936279521919[48] = 0;
   out_2959270936279521919[49] = 0;
   out_2959270936279521919[50] = 0;
   out_2959270936279521919[51] = 0;
   out_2959270936279521919[52] = 0;
   out_2959270936279521919[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8810353316368700687) {
  err_fun(nom_x, delta_x, out_8810353316368700687);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8282119777185922813) {
  inv_err_fun(nom_x, true_x, out_8282119777185922813);
}
void pose_H_mod_fun(double *state, double *out_9067879162073671719) {
  H_mod_fun(state, out_9067879162073671719);
}
void pose_f_fun(double *state, double dt, double *out_6384990450931193177) {
  f_fun(state,  dt, out_6384990450931193177);
}
void pose_F_fun(double *state, double dt, double *out_105498423206002474) {
  F_fun(state,  dt, out_105498423206002474);
}
void pose_h_4(double *state, double *unused, double *out_3142206333536839736) {
  h_4(state, unused, out_3142206333536839736);
}
void pose_H_4(double *state, double *unused, double *out_123517496015850377) {
  H_4(state, unused, out_123517496015850377);
}
void pose_h_10(double *state, double *unused, double *out_7019642631864442983) {
  h_10(state, unused, out_7019642631864442983);
}
void pose_H_10(double *state, double *unused, double *out_8619357166475704864) {
  H_10(state, unused, out_8619357166475704864);
}
void pose_h_13(double *state, double *unused, double *out_7946660746268207299) {
  h_13(state, unused, out_7946660746268207299);
}
void pose_H_13(double *state, double *unused, double *out_3710237967286673647) {
  H_13(state, unused, out_3710237967286673647);
}
void pose_h_14(double *state, double *unused, double *out_6202390496101391785) {
  h_14(state, unused, out_6202390496101391785);
}
void pose_H_14(double *state, double *unused, double *out_2959270936279521919) {
  H_14(state, unused, out_2959270936279521919);
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
