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
void err_fun(double *nom_x, double *delta_x, double *out_8958383251573640) {
   out_8958383251573640[0] = delta_x[0] + nom_x[0];
   out_8958383251573640[1] = delta_x[1] + nom_x[1];
   out_8958383251573640[2] = delta_x[2] + nom_x[2];
   out_8958383251573640[3] = delta_x[3] + nom_x[3];
   out_8958383251573640[4] = delta_x[4] + nom_x[4];
   out_8958383251573640[5] = delta_x[5] + nom_x[5];
   out_8958383251573640[6] = delta_x[6] + nom_x[6];
   out_8958383251573640[7] = delta_x[7] + nom_x[7];
   out_8958383251573640[8] = delta_x[8] + nom_x[8];
   out_8958383251573640[9] = delta_x[9] + nom_x[9];
   out_8958383251573640[10] = delta_x[10] + nom_x[10];
   out_8958383251573640[11] = delta_x[11] + nom_x[11];
   out_8958383251573640[12] = delta_x[12] + nom_x[12];
   out_8958383251573640[13] = delta_x[13] + nom_x[13];
   out_8958383251573640[14] = delta_x[14] + nom_x[14];
   out_8958383251573640[15] = delta_x[15] + nom_x[15];
   out_8958383251573640[16] = delta_x[16] + nom_x[16];
   out_8958383251573640[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3510167321874192836) {
   out_3510167321874192836[0] = -nom_x[0] + true_x[0];
   out_3510167321874192836[1] = -nom_x[1] + true_x[1];
   out_3510167321874192836[2] = -nom_x[2] + true_x[2];
   out_3510167321874192836[3] = -nom_x[3] + true_x[3];
   out_3510167321874192836[4] = -nom_x[4] + true_x[4];
   out_3510167321874192836[5] = -nom_x[5] + true_x[5];
   out_3510167321874192836[6] = -nom_x[6] + true_x[6];
   out_3510167321874192836[7] = -nom_x[7] + true_x[7];
   out_3510167321874192836[8] = -nom_x[8] + true_x[8];
   out_3510167321874192836[9] = -nom_x[9] + true_x[9];
   out_3510167321874192836[10] = -nom_x[10] + true_x[10];
   out_3510167321874192836[11] = -nom_x[11] + true_x[11];
   out_3510167321874192836[12] = -nom_x[12] + true_x[12];
   out_3510167321874192836[13] = -nom_x[13] + true_x[13];
   out_3510167321874192836[14] = -nom_x[14] + true_x[14];
   out_3510167321874192836[15] = -nom_x[15] + true_x[15];
   out_3510167321874192836[16] = -nom_x[16] + true_x[16];
   out_3510167321874192836[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_10314592692584858) {
   out_10314592692584858[0] = 1.0;
   out_10314592692584858[1] = 0.0;
   out_10314592692584858[2] = 0.0;
   out_10314592692584858[3] = 0.0;
   out_10314592692584858[4] = 0.0;
   out_10314592692584858[5] = 0.0;
   out_10314592692584858[6] = 0.0;
   out_10314592692584858[7] = 0.0;
   out_10314592692584858[8] = 0.0;
   out_10314592692584858[9] = 0.0;
   out_10314592692584858[10] = 0.0;
   out_10314592692584858[11] = 0.0;
   out_10314592692584858[12] = 0.0;
   out_10314592692584858[13] = 0.0;
   out_10314592692584858[14] = 0.0;
   out_10314592692584858[15] = 0.0;
   out_10314592692584858[16] = 0.0;
   out_10314592692584858[17] = 0.0;
   out_10314592692584858[18] = 0.0;
   out_10314592692584858[19] = 1.0;
   out_10314592692584858[20] = 0.0;
   out_10314592692584858[21] = 0.0;
   out_10314592692584858[22] = 0.0;
   out_10314592692584858[23] = 0.0;
   out_10314592692584858[24] = 0.0;
   out_10314592692584858[25] = 0.0;
   out_10314592692584858[26] = 0.0;
   out_10314592692584858[27] = 0.0;
   out_10314592692584858[28] = 0.0;
   out_10314592692584858[29] = 0.0;
   out_10314592692584858[30] = 0.0;
   out_10314592692584858[31] = 0.0;
   out_10314592692584858[32] = 0.0;
   out_10314592692584858[33] = 0.0;
   out_10314592692584858[34] = 0.0;
   out_10314592692584858[35] = 0.0;
   out_10314592692584858[36] = 0.0;
   out_10314592692584858[37] = 0.0;
   out_10314592692584858[38] = 1.0;
   out_10314592692584858[39] = 0.0;
   out_10314592692584858[40] = 0.0;
   out_10314592692584858[41] = 0.0;
   out_10314592692584858[42] = 0.0;
   out_10314592692584858[43] = 0.0;
   out_10314592692584858[44] = 0.0;
   out_10314592692584858[45] = 0.0;
   out_10314592692584858[46] = 0.0;
   out_10314592692584858[47] = 0.0;
   out_10314592692584858[48] = 0.0;
   out_10314592692584858[49] = 0.0;
   out_10314592692584858[50] = 0.0;
   out_10314592692584858[51] = 0.0;
   out_10314592692584858[52] = 0.0;
   out_10314592692584858[53] = 0.0;
   out_10314592692584858[54] = 0.0;
   out_10314592692584858[55] = 0.0;
   out_10314592692584858[56] = 0.0;
   out_10314592692584858[57] = 1.0;
   out_10314592692584858[58] = 0.0;
   out_10314592692584858[59] = 0.0;
   out_10314592692584858[60] = 0.0;
   out_10314592692584858[61] = 0.0;
   out_10314592692584858[62] = 0.0;
   out_10314592692584858[63] = 0.0;
   out_10314592692584858[64] = 0.0;
   out_10314592692584858[65] = 0.0;
   out_10314592692584858[66] = 0.0;
   out_10314592692584858[67] = 0.0;
   out_10314592692584858[68] = 0.0;
   out_10314592692584858[69] = 0.0;
   out_10314592692584858[70] = 0.0;
   out_10314592692584858[71] = 0.0;
   out_10314592692584858[72] = 0.0;
   out_10314592692584858[73] = 0.0;
   out_10314592692584858[74] = 0.0;
   out_10314592692584858[75] = 0.0;
   out_10314592692584858[76] = 1.0;
   out_10314592692584858[77] = 0.0;
   out_10314592692584858[78] = 0.0;
   out_10314592692584858[79] = 0.0;
   out_10314592692584858[80] = 0.0;
   out_10314592692584858[81] = 0.0;
   out_10314592692584858[82] = 0.0;
   out_10314592692584858[83] = 0.0;
   out_10314592692584858[84] = 0.0;
   out_10314592692584858[85] = 0.0;
   out_10314592692584858[86] = 0.0;
   out_10314592692584858[87] = 0.0;
   out_10314592692584858[88] = 0.0;
   out_10314592692584858[89] = 0.0;
   out_10314592692584858[90] = 0.0;
   out_10314592692584858[91] = 0.0;
   out_10314592692584858[92] = 0.0;
   out_10314592692584858[93] = 0.0;
   out_10314592692584858[94] = 0.0;
   out_10314592692584858[95] = 1.0;
   out_10314592692584858[96] = 0.0;
   out_10314592692584858[97] = 0.0;
   out_10314592692584858[98] = 0.0;
   out_10314592692584858[99] = 0.0;
   out_10314592692584858[100] = 0.0;
   out_10314592692584858[101] = 0.0;
   out_10314592692584858[102] = 0.0;
   out_10314592692584858[103] = 0.0;
   out_10314592692584858[104] = 0.0;
   out_10314592692584858[105] = 0.0;
   out_10314592692584858[106] = 0.0;
   out_10314592692584858[107] = 0.0;
   out_10314592692584858[108] = 0.0;
   out_10314592692584858[109] = 0.0;
   out_10314592692584858[110] = 0.0;
   out_10314592692584858[111] = 0.0;
   out_10314592692584858[112] = 0.0;
   out_10314592692584858[113] = 0.0;
   out_10314592692584858[114] = 1.0;
   out_10314592692584858[115] = 0.0;
   out_10314592692584858[116] = 0.0;
   out_10314592692584858[117] = 0.0;
   out_10314592692584858[118] = 0.0;
   out_10314592692584858[119] = 0.0;
   out_10314592692584858[120] = 0.0;
   out_10314592692584858[121] = 0.0;
   out_10314592692584858[122] = 0.0;
   out_10314592692584858[123] = 0.0;
   out_10314592692584858[124] = 0.0;
   out_10314592692584858[125] = 0.0;
   out_10314592692584858[126] = 0.0;
   out_10314592692584858[127] = 0.0;
   out_10314592692584858[128] = 0.0;
   out_10314592692584858[129] = 0.0;
   out_10314592692584858[130] = 0.0;
   out_10314592692584858[131] = 0.0;
   out_10314592692584858[132] = 0.0;
   out_10314592692584858[133] = 1.0;
   out_10314592692584858[134] = 0.0;
   out_10314592692584858[135] = 0.0;
   out_10314592692584858[136] = 0.0;
   out_10314592692584858[137] = 0.0;
   out_10314592692584858[138] = 0.0;
   out_10314592692584858[139] = 0.0;
   out_10314592692584858[140] = 0.0;
   out_10314592692584858[141] = 0.0;
   out_10314592692584858[142] = 0.0;
   out_10314592692584858[143] = 0.0;
   out_10314592692584858[144] = 0.0;
   out_10314592692584858[145] = 0.0;
   out_10314592692584858[146] = 0.0;
   out_10314592692584858[147] = 0.0;
   out_10314592692584858[148] = 0.0;
   out_10314592692584858[149] = 0.0;
   out_10314592692584858[150] = 0.0;
   out_10314592692584858[151] = 0.0;
   out_10314592692584858[152] = 1.0;
   out_10314592692584858[153] = 0.0;
   out_10314592692584858[154] = 0.0;
   out_10314592692584858[155] = 0.0;
   out_10314592692584858[156] = 0.0;
   out_10314592692584858[157] = 0.0;
   out_10314592692584858[158] = 0.0;
   out_10314592692584858[159] = 0.0;
   out_10314592692584858[160] = 0.0;
   out_10314592692584858[161] = 0.0;
   out_10314592692584858[162] = 0.0;
   out_10314592692584858[163] = 0.0;
   out_10314592692584858[164] = 0.0;
   out_10314592692584858[165] = 0.0;
   out_10314592692584858[166] = 0.0;
   out_10314592692584858[167] = 0.0;
   out_10314592692584858[168] = 0.0;
   out_10314592692584858[169] = 0.0;
   out_10314592692584858[170] = 0.0;
   out_10314592692584858[171] = 1.0;
   out_10314592692584858[172] = 0.0;
   out_10314592692584858[173] = 0.0;
   out_10314592692584858[174] = 0.0;
   out_10314592692584858[175] = 0.0;
   out_10314592692584858[176] = 0.0;
   out_10314592692584858[177] = 0.0;
   out_10314592692584858[178] = 0.0;
   out_10314592692584858[179] = 0.0;
   out_10314592692584858[180] = 0.0;
   out_10314592692584858[181] = 0.0;
   out_10314592692584858[182] = 0.0;
   out_10314592692584858[183] = 0.0;
   out_10314592692584858[184] = 0.0;
   out_10314592692584858[185] = 0.0;
   out_10314592692584858[186] = 0.0;
   out_10314592692584858[187] = 0.0;
   out_10314592692584858[188] = 0.0;
   out_10314592692584858[189] = 0.0;
   out_10314592692584858[190] = 1.0;
   out_10314592692584858[191] = 0.0;
   out_10314592692584858[192] = 0.0;
   out_10314592692584858[193] = 0.0;
   out_10314592692584858[194] = 0.0;
   out_10314592692584858[195] = 0.0;
   out_10314592692584858[196] = 0.0;
   out_10314592692584858[197] = 0.0;
   out_10314592692584858[198] = 0.0;
   out_10314592692584858[199] = 0.0;
   out_10314592692584858[200] = 0.0;
   out_10314592692584858[201] = 0.0;
   out_10314592692584858[202] = 0.0;
   out_10314592692584858[203] = 0.0;
   out_10314592692584858[204] = 0.0;
   out_10314592692584858[205] = 0.0;
   out_10314592692584858[206] = 0.0;
   out_10314592692584858[207] = 0.0;
   out_10314592692584858[208] = 0.0;
   out_10314592692584858[209] = 1.0;
   out_10314592692584858[210] = 0.0;
   out_10314592692584858[211] = 0.0;
   out_10314592692584858[212] = 0.0;
   out_10314592692584858[213] = 0.0;
   out_10314592692584858[214] = 0.0;
   out_10314592692584858[215] = 0.0;
   out_10314592692584858[216] = 0.0;
   out_10314592692584858[217] = 0.0;
   out_10314592692584858[218] = 0.0;
   out_10314592692584858[219] = 0.0;
   out_10314592692584858[220] = 0.0;
   out_10314592692584858[221] = 0.0;
   out_10314592692584858[222] = 0.0;
   out_10314592692584858[223] = 0.0;
   out_10314592692584858[224] = 0.0;
   out_10314592692584858[225] = 0.0;
   out_10314592692584858[226] = 0.0;
   out_10314592692584858[227] = 0.0;
   out_10314592692584858[228] = 1.0;
   out_10314592692584858[229] = 0.0;
   out_10314592692584858[230] = 0.0;
   out_10314592692584858[231] = 0.0;
   out_10314592692584858[232] = 0.0;
   out_10314592692584858[233] = 0.0;
   out_10314592692584858[234] = 0.0;
   out_10314592692584858[235] = 0.0;
   out_10314592692584858[236] = 0.0;
   out_10314592692584858[237] = 0.0;
   out_10314592692584858[238] = 0.0;
   out_10314592692584858[239] = 0.0;
   out_10314592692584858[240] = 0.0;
   out_10314592692584858[241] = 0.0;
   out_10314592692584858[242] = 0.0;
   out_10314592692584858[243] = 0.0;
   out_10314592692584858[244] = 0.0;
   out_10314592692584858[245] = 0.0;
   out_10314592692584858[246] = 0.0;
   out_10314592692584858[247] = 1.0;
   out_10314592692584858[248] = 0.0;
   out_10314592692584858[249] = 0.0;
   out_10314592692584858[250] = 0.0;
   out_10314592692584858[251] = 0.0;
   out_10314592692584858[252] = 0.0;
   out_10314592692584858[253] = 0.0;
   out_10314592692584858[254] = 0.0;
   out_10314592692584858[255] = 0.0;
   out_10314592692584858[256] = 0.0;
   out_10314592692584858[257] = 0.0;
   out_10314592692584858[258] = 0.0;
   out_10314592692584858[259] = 0.0;
   out_10314592692584858[260] = 0.0;
   out_10314592692584858[261] = 0.0;
   out_10314592692584858[262] = 0.0;
   out_10314592692584858[263] = 0.0;
   out_10314592692584858[264] = 0.0;
   out_10314592692584858[265] = 0.0;
   out_10314592692584858[266] = 1.0;
   out_10314592692584858[267] = 0.0;
   out_10314592692584858[268] = 0.0;
   out_10314592692584858[269] = 0.0;
   out_10314592692584858[270] = 0.0;
   out_10314592692584858[271] = 0.0;
   out_10314592692584858[272] = 0.0;
   out_10314592692584858[273] = 0.0;
   out_10314592692584858[274] = 0.0;
   out_10314592692584858[275] = 0.0;
   out_10314592692584858[276] = 0.0;
   out_10314592692584858[277] = 0.0;
   out_10314592692584858[278] = 0.0;
   out_10314592692584858[279] = 0.0;
   out_10314592692584858[280] = 0.0;
   out_10314592692584858[281] = 0.0;
   out_10314592692584858[282] = 0.0;
   out_10314592692584858[283] = 0.0;
   out_10314592692584858[284] = 0.0;
   out_10314592692584858[285] = 1.0;
   out_10314592692584858[286] = 0.0;
   out_10314592692584858[287] = 0.0;
   out_10314592692584858[288] = 0.0;
   out_10314592692584858[289] = 0.0;
   out_10314592692584858[290] = 0.0;
   out_10314592692584858[291] = 0.0;
   out_10314592692584858[292] = 0.0;
   out_10314592692584858[293] = 0.0;
   out_10314592692584858[294] = 0.0;
   out_10314592692584858[295] = 0.0;
   out_10314592692584858[296] = 0.0;
   out_10314592692584858[297] = 0.0;
   out_10314592692584858[298] = 0.0;
   out_10314592692584858[299] = 0.0;
   out_10314592692584858[300] = 0.0;
   out_10314592692584858[301] = 0.0;
   out_10314592692584858[302] = 0.0;
   out_10314592692584858[303] = 0.0;
   out_10314592692584858[304] = 1.0;
   out_10314592692584858[305] = 0.0;
   out_10314592692584858[306] = 0.0;
   out_10314592692584858[307] = 0.0;
   out_10314592692584858[308] = 0.0;
   out_10314592692584858[309] = 0.0;
   out_10314592692584858[310] = 0.0;
   out_10314592692584858[311] = 0.0;
   out_10314592692584858[312] = 0.0;
   out_10314592692584858[313] = 0.0;
   out_10314592692584858[314] = 0.0;
   out_10314592692584858[315] = 0.0;
   out_10314592692584858[316] = 0.0;
   out_10314592692584858[317] = 0.0;
   out_10314592692584858[318] = 0.0;
   out_10314592692584858[319] = 0.0;
   out_10314592692584858[320] = 0.0;
   out_10314592692584858[321] = 0.0;
   out_10314592692584858[322] = 0.0;
   out_10314592692584858[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_3469176563342886468) {
   out_3469176563342886468[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_3469176563342886468[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_3469176563342886468[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_3469176563342886468[3] = dt*state[12] + state[3];
   out_3469176563342886468[4] = dt*state[13] + state[4];
   out_3469176563342886468[5] = dt*state[14] + state[5];
   out_3469176563342886468[6] = state[6];
   out_3469176563342886468[7] = state[7];
   out_3469176563342886468[8] = state[8];
   out_3469176563342886468[9] = state[9];
   out_3469176563342886468[10] = state[10];
   out_3469176563342886468[11] = state[11];
   out_3469176563342886468[12] = state[12];
   out_3469176563342886468[13] = state[13];
   out_3469176563342886468[14] = state[14];
   out_3469176563342886468[15] = state[15];
   out_3469176563342886468[16] = state[16];
   out_3469176563342886468[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6053143964145098388) {
   out_6053143964145098388[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6053143964145098388[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6053143964145098388[2] = 0;
   out_6053143964145098388[3] = 0;
   out_6053143964145098388[4] = 0;
   out_6053143964145098388[5] = 0;
   out_6053143964145098388[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6053143964145098388[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6053143964145098388[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6053143964145098388[9] = 0;
   out_6053143964145098388[10] = 0;
   out_6053143964145098388[11] = 0;
   out_6053143964145098388[12] = 0;
   out_6053143964145098388[13] = 0;
   out_6053143964145098388[14] = 0;
   out_6053143964145098388[15] = 0;
   out_6053143964145098388[16] = 0;
   out_6053143964145098388[17] = 0;
   out_6053143964145098388[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6053143964145098388[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6053143964145098388[20] = 0;
   out_6053143964145098388[21] = 0;
   out_6053143964145098388[22] = 0;
   out_6053143964145098388[23] = 0;
   out_6053143964145098388[24] = 0;
   out_6053143964145098388[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6053143964145098388[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6053143964145098388[27] = 0;
   out_6053143964145098388[28] = 0;
   out_6053143964145098388[29] = 0;
   out_6053143964145098388[30] = 0;
   out_6053143964145098388[31] = 0;
   out_6053143964145098388[32] = 0;
   out_6053143964145098388[33] = 0;
   out_6053143964145098388[34] = 0;
   out_6053143964145098388[35] = 0;
   out_6053143964145098388[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6053143964145098388[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6053143964145098388[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6053143964145098388[39] = 0;
   out_6053143964145098388[40] = 0;
   out_6053143964145098388[41] = 0;
   out_6053143964145098388[42] = 0;
   out_6053143964145098388[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6053143964145098388[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6053143964145098388[45] = 0;
   out_6053143964145098388[46] = 0;
   out_6053143964145098388[47] = 0;
   out_6053143964145098388[48] = 0;
   out_6053143964145098388[49] = 0;
   out_6053143964145098388[50] = 0;
   out_6053143964145098388[51] = 0;
   out_6053143964145098388[52] = 0;
   out_6053143964145098388[53] = 0;
   out_6053143964145098388[54] = 0;
   out_6053143964145098388[55] = 0;
   out_6053143964145098388[56] = 0;
   out_6053143964145098388[57] = 1;
   out_6053143964145098388[58] = 0;
   out_6053143964145098388[59] = 0;
   out_6053143964145098388[60] = 0;
   out_6053143964145098388[61] = 0;
   out_6053143964145098388[62] = 0;
   out_6053143964145098388[63] = 0;
   out_6053143964145098388[64] = 0;
   out_6053143964145098388[65] = 0;
   out_6053143964145098388[66] = dt;
   out_6053143964145098388[67] = 0;
   out_6053143964145098388[68] = 0;
   out_6053143964145098388[69] = 0;
   out_6053143964145098388[70] = 0;
   out_6053143964145098388[71] = 0;
   out_6053143964145098388[72] = 0;
   out_6053143964145098388[73] = 0;
   out_6053143964145098388[74] = 0;
   out_6053143964145098388[75] = 0;
   out_6053143964145098388[76] = 1;
   out_6053143964145098388[77] = 0;
   out_6053143964145098388[78] = 0;
   out_6053143964145098388[79] = 0;
   out_6053143964145098388[80] = 0;
   out_6053143964145098388[81] = 0;
   out_6053143964145098388[82] = 0;
   out_6053143964145098388[83] = 0;
   out_6053143964145098388[84] = 0;
   out_6053143964145098388[85] = dt;
   out_6053143964145098388[86] = 0;
   out_6053143964145098388[87] = 0;
   out_6053143964145098388[88] = 0;
   out_6053143964145098388[89] = 0;
   out_6053143964145098388[90] = 0;
   out_6053143964145098388[91] = 0;
   out_6053143964145098388[92] = 0;
   out_6053143964145098388[93] = 0;
   out_6053143964145098388[94] = 0;
   out_6053143964145098388[95] = 1;
   out_6053143964145098388[96] = 0;
   out_6053143964145098388[97] = 0;
   out_6053143964145098388[98] = 0;
   out_6053143964145098388[99] = 0;
   out_6053143964145098388[100] = 0;
   out_6053143964145098388[101] = 0;
   out_6053143964145098388[102] = 0;
   out_6053143964145098388[103] = 0;
   out_6053143964145098388[104] = dt;
   out_6053143964145098388[105] = 0;
   out_6053143964145098388[106] = 0;
   out_6053143964145098388[107] = 0;
   out_6053143964145098388[108] = 0;
   out_6053143964145098388[109] = 0;
   out_6053143964145098388[110] = 0;
   out_6053143964145098388[111] = 0;
   out_6053143964145098388[112] = 0;
   out_6053143964145098388[113] = 0;
   out_6053143964145098388[114] = 1;
   out_6053143964145098388[115] = 0;
   out_6053143964145098388[116] = 0;
   out_6053143964145098388[117] = 0;
   out_6053143964145098388[118] = 0;
   out_6053143964145098388[119] = 0;
   out_6053143964145098388[120] = 0;
   out_6053143964145098388[121] = 0;
   out_6053143964145098388[122] = 0;
   out_6053143964145098388[123] = 0;
   out_6053143964145098388[124] = 0;
   out_6053143964145098388[125] = 0;
   out_6053143964145098388[126] = 0;
   out_6053143964145098388[127] = 0;
   out_6053143964145098388[128] = 0;
   out_6053143964145098388[129] = 0;
   out_6053143964145098388[130] = 0;
   out_6053143964145098388[131] = 0;
   out_6053143964145098388[132] = 0;
   out_6053143964145098388[133] = 1;
   out_6053143964145098388[134] = 0;
   out_6053143964145098388[135] = 0;
   out_6053143964145098388[136] = 0;
   out_6053143964145098388[137] = 0;
   out_6053143964145098388[138] = 0;
   out_6053143964145098388[139] = 0;
   out_6053143964145098388[140] = 0;
   out_6053143964145098388[141] = 0;
   out_6053143964145098388[142] = 0;
   out_6053143964145098388[143] = 0;
   out_6053143964145098388[144] = 0;
   out_6053143964145098388[145] = 0;
   out_6053143964145098388[146] = 0;
   out_6053143964145098388[147] = 0;
   out_6053143964145098388[148] = 0;
   out_6053143964145098388[149] = 0;
   out_6053143964145098388[150] = 0;
   out_6053143964145098388[151] = 0;
   out_6053143964145098388[152] = 1;
   out_6053143964145098388[153] = 0;
   out_6053143964145098388[154] = 0;
   out_6053143964145098388[155] = 0;
   out_6053143964145098388[156] = 0;
   out_6053143964145098388[157] = 0;
   out_6053143964145098388[158] = 0;
   out_6053143964145098388[159] = 0;
   out_6053143964145098388[160] = 0;
   out_6053143964145098388[161] = 0;
   out_6053143964145098388[162] = 0;
   out_6053143964145098388[163] = 0;
   out_6053143964145098388[164] = 0;
   out_6053143964145098388[165] = 0;
   out_6053143964145098388[166] = 0;
   out_6053143964145098388[167] = 0;
   out_6053143964145098388[168] = 0;
   out_6053143964145098388[169] = 0;
   out_6053143964145098388[170] = 0;
   out_6053143964145098388[171] = 1;
   out_6053143964145098388[172] = 0;
   out_6053143964145098388[173] = 0;
   out_6053143964145098388[174] = 0;
   out_6053143964145098388[175] = 0;
   out_6053143964145098388[176] = 0;
   out_6053143964145098388[177] = 0;
   out_6053143964145098388[178] = 0;
   out_6053143964145098388[179] = 0;
   out_6053143964145098388[180] = 0;
   out_6053143964145098388[181] = 0;
   out_6053143964145098388[182] = 0;
   out_6053143964145098388[183] = 0;
   out_6053143964145098388[184] = 0;
   out_6053143964145098388[185] = 0;
   out_6053143964145098388[186] = 0;
   out_6053143964145098388[187] = 0;
   out_6053143964145098388[188] = 0;
   out_6053143964145098388[189] = 0;
   out_6053143964145098388[190] = 1;
   out_6053143964145098388[191] = 0;
   out_6053143964145098388[192] = 0;
   out_6053143964145098388[193] = 0;
   out_6053143964145098388[194] = 0;
   out_6053143964145098388[195] = 0;
   out_6053143964145098388[196] = 0;
   out_6053143964145098388[197] = 0;
   out_6053143964145098388[198] = 0;
   out_6053143964145098388[199] = 0;
   out_6053143964145098388[200] = 0;
   out_6053143964145098388[201] = 0;
   out_6053143964145098388[202] = 0;
   out_6053143964145098388[203] = 0;
   out_6053143964145098388[204] = 0;
   out_6053143964145098388[205] = 0;
   out_6053143964145098388[206] = 0;
   out_6053143964145098388[207] = 0;
   out_6053143964145098388[208] = 0;
   out_6053143964145098388[209] = 1;
   out_6053143964145098388[210] = 0;
   out_6053143964145098388[211] = 0;
   out_6053143964145098388[212] = 0;
   out_6053143964145098388[213] = 0;
   out_6053143964145098388[214] = 0;
   out_6053143964145098388[215] = 0;
   out_6053143964145098388[216] = 0;
   out_6053143964145098388[217] = 0;
   out_6053143964145098388[218] = 0;
   out_6053143964145098388[219] = 0;
   out_6053143964145098388[220] = 0;
   out_6053143964145098388[221] = 0;
   out_6053143964145098388[222] = 0;
   out_6053143964145098388[223] = 0;
   out_6053143964145098388[224] = 0;
   out_6053143964145098388[225] = 0;
   out_6053143964145098388[226] = 0;
   out_6053143964145098388[227] = 0;
   out_6053143964145098388[228] = 1;
   out_6053143964145098388[229] = 0;
   out_6053143964145098388[230] = 0;
   out_6053143964145098388[231] = 0;
   out_6053143964145098388[232] = 0;
   out_6053143964145098388[233] = 0;
   out_6053143964145098388[234] = 0;
   out_6053143964145098388[235] = 0;
   out_6053143964145098388[236] = 0;
   out_6053143964145098388[237] = 0;
   out_6053143964145098388[238] = 0;
   out_6053143964145098388[239] = 0;
   out_6053143964145098388[240] = 0;
   out_6053143964145098388[241] = 0;
   out_6053143964145098388[242] = 0;
   out_6053143964145098388[243] = 0;
   out_6053143964145098388[244] = 0;
   out_6053143964145098388[245] = 0;
   out_6053143964145098388[246] = 0;
   out_6053143964145098388[247] = 1;
   out_6053143964145098388[248] = 0;
   out_6053143964145098388[249] = 0;
   out_6053143964145098388[250] = 0;
   out_6053143964145098388[251] = 0;
   out_6053143964145098388[252] = 0;
   out_6053143964145098388[253] = 0;
   out_6053143964145098388[254] = 0;
   out_6053143964145098388[255] = 0;
   out_6053143964145098388[256] = 0;
   out_6053143964145098388[257] = 0;
   out_6053143964145098388[258] = 0;
   out_6053143964145098388[259] = 0;
   out_6053143964145098388[260] = 0;
   out_6053143964145098388[261] = 0;
   out_6053143964145098388[262] = 0;
   out_6053143964145098388[263] = 0;
   out_6053143964145098388[264] = 0;
   out_6053143964145098388[265] = 0;
   out_6053143964145098388[266] = 1;
   out_6053143964145098388[267] = 0;
   out_6053143964145098388[268] = 0;
   out_6053143964145098388[269] = 0;
   out_6053143964145098388[270] = 0;
   out_6053143964145098388[271] = 0;
   out_6053143964145098388[272] = 0;
   out_6053143964145098388[273] = 0;
   out_6053143964145098388[274] = 0;
   out_6053143964145098388[275] = 0;
   out_6053143964145098388[276] = 0;
   out_6053143964145098388[277] = 0;
   out_6053143964145098388[278] = 0;
   out_6053143964145098388[279] = 0;
   out_6053143964145098388[280] = 0;
   out_6053143964145098388[281] = 0;
   out_6053143964145098388[282] = 0;
   out_6053143964145098388[283] = 0;
   out_6053143964145098388[284] = 0;
   out_6053143964145098388[285] = 1;
   out_6053143964145098388[286] = 0;
   out_6053143964145098388[287] = 0;
   out_6053143964145098388[288] = 0;
   out_6053143964145098388[289] = 0;
   out_6053143964145098388[290] = 0;
   out_6053143964145098388[291] = 0;
   out_6053143964145098388[292] = 0;
   out_6053143964145098388[293] = 0;
   out_6053143964145098388[294] = 0;
   out_6053143964145098388[295] = 0;
   out_6053143964145098388[296] = 0;
   out_6053143964145098388[297] = 0;
   out_6053143964145098388[298] = 0;
   out_6053143964145098388[299] = 0;
   out_6053143964145098388[300] = 0;
   out_6053143964145098388[301] = 0;
   out_6053143964145098388[302] = 0;
   out_6053143964145098388[303] = 0;
   out_6053143964145098388[304] = 1;
   out_6053143964145098388[305] = 0;
   out_6053143964145098388[306] = 0;
   out_6053143964145098388[307] = 0;
   out_6053143964145098388[308] = 0;
   out_6053143964145098388[309] = 0;
   out_6053143964145098388[310] = 0;
   out_6053143964145098388[311] = 0;
   out_6053143964145098388[312] = 0;
   out_6053143964145098388[313] = 0;
   out_6053143964145098388[314] = 0;
   out_6053143964145098388[315] = 0;
   out_6053143964145098388[316] = 0;
   out_6053143964145098388[317] = 0;
   out_6053143964145098388[318] = 0;
   out_6053143964145098388[319] = 0;
   out_6053143964145098388[320] = 0;
   out_6053143964145098388[321] = 0;
   out_6053143964145098388[322] = 0;
   out_6053143964145098388[323] = 1;
}
void h_4(double *state, double *unused, double *out_4331217932147478278) {
   out_4331217932147478278[0] = state[6] + state[9];
   out_4331217932147478278[1] = state[7] + state[10];
   out_4331217932147478278[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_3761492617151322714) {
   out_3761492617151322714[0] = 0;
   out_3761492617151322714[1] = 0;
   out_3761492617151322714[2] = 0;
   out_3761492617151322714[3] = 0;
   out_3761492617151322714[4] = 0;
   out_3761492617151322714[5] = 0;
   out_3761492617151322714[6] = 1;
   out_3761492617151322714[7] = 0;
   out_3761492617151322714[8] = 0;
   out_3761492617151322714[9] = 1;
   out_3761492617151322714[10] = 0;
   out_3761492617151322714[11] = 0;
   out_3761492617151322714[12] = 0;
   out_3761492617151322714[13] = 0;
   out_3761492617151322714[14] = 0;
   out_3761492617151322714[15] = 0;
   out_3761492617151322714[16] = 0;
   out_3761492617151322714[17] = 0;
   out_3761492617151322714[18] = 0;
   out_3761492617151322714[19] = 0;
   out_3761492617151322714[20] = 0;
   out_3761492617151322714[21] = 0;
   out_3761492617151322714[22] = 0;
   out_3761492617151322714[23] = 0;
   out_3761492617151322714[24] = 0;
   out_3761492617151322714[25] = 1;
   out_3761492617151322714[26] = 0;
   out_3761492617151322714[27] = 0;
   out_3761492617151322714[28] = 1;
   out_3761492617151322714[29] = 0;
   out_3761492617151322714[30] = 0;
   out_3761492617151322714[31] = 0;
   out_3761492617151322714[32] = 0;
   out_3761492617151322714[33] = 0;
   out_3761492617151322714[34] = 0;
   out_3761492617151322714[35] = 0;
   out_3761492617151322714[36] = 0;
   out_3761492617151322714[37] = 0;
   out_3761492617151322714[38] = 0;
   out_3761492617151322714[39] = 0;
   out_3761492617151322714[40] = 0;
   out_3761492617151322714[41] = 0;
   out_3761492617151322714[42] = 0;
   out_3761492617151322714[43] = 0;
   out_3761492617151322714[44] = 1;
   out_3761492617151322714[45] = 0;
   out_3761492617151322714[46] = 0;
   out_3761492617151322714[47] = 1;
   out_3761492617151322714[48] = 0;
   out_3761492617151322714[49] = 0;
   out_3761492617151322714[50] = 0;
   out_3761492617151322714[51] = 0;
   out_3761492617151322714[52] = 0;
   out_3761492617151322714[53] = 0;
}
void h_10(double *state, double *unused, double *out_1904703987337421912) {
   out_1904703987337421912[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_1904703987337421912[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_1904703987337421912[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4366147958481579120) {
   out_4366147958481579120[0] = 0;
   out_4366147958481579120[1] = 9.8100000000000005*cos(state[1]);
   out_4366147958481579120[2] = 0;
   out_4366147958481579120[3] = 0;
   out_4366147958481579120[4] = -state[8];
   out_4366147958481579120[5] = state[7];
   out_4366147958481579120[6] = 0;
   out_4366147958481579120[7] = state[5];
   out_4366147958481579120[8] = -state[4];
   out_4366147958481579120[9] = 0;
   out_4366147958481579120[10] = 0;
   out_4366147958481579120[11] = 0;
   out_4366147958481579120[12] = 1;
   out_4366147958481579120[13] = 0;
   out_4366147958481579120[14] = 0;
   out_4366147958481579120[15] = 1;
   out_4366147958481579120[16] = 0;
   out_4366147958481579120[17] = 0;
   out_4366147958481579120[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4366147958481579120[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4366147958481579120[20] = 0;
   out_4366147958481579120[21] = state[8];
   out_4366147958481579120[22] = 0;
   out_4366147958481579120[23] = -state[6];
   out_4366147958481579120[24] = -state[5];
   out_4366147958481579120[25] = 0;
   out_4366147958481579120[26] = state[3];
   out_4366147958481579120[27] = 0;
   out_4366147958481579120[28] = 0;
   out_4366147958481579120[29] = 0;
   out_4366147958481579120[30] = 0;
   out_4366147958481579120[31] = 1;
   out_4366147958481579120[32] = 0;
   out_4366147958481579120[33] = 0;
   out_4366147958481579120[34] = 1;
   out_4366147958481579120[35] = 0;
   out_4366147958481579120[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4366147958481579120[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4366147958481579120[38] = 0;
   out_4366147958481579120[39] = -state[7];
   out_4366147958481579120[40] = state[6];
   out_4366147958481579120[41] = 0;
   out_4366147958481579120[42] = state[4];
   out_4366147958481579120[43] = -state[3];
   out_4366147958481579120[44] = 0;
   out_4366147958481579120[45] = 0;
   out_4366147958481579120[46] = 0;
   out_4366147958481579120[47] = 0;
   out_4366147958481579120[48] = 0;
   out_4366147958481579120[49] = 0;
   out_4366147958481579120[50] = 1;
   out_4366147958481579120[51] = 0;
   out_4366147958481579120[52] = 0;
   out_4366147958481579120[53] = 1;
}
void h_13(double *state, double *unused, double *out_9149454562438237975) {
   out_9149454562438237975[0] = state[3];
   out_9149454562438237975[1] = state[4];
   out_9149454562438237975[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6973766442483655515) {
   out_6973766442483655515[0] = 0;
   out_6973766442483655515[1] = 0;
   out_6973766442483655515[2] = 0;
   out_6973766442483655515[3] = 1;
   out_6973766442483655515[4] = 0;
   out_6973766442483655515[5] = 0;
   out_6973766442483655515[6] = 0;
   out_6973766442483655515[7] = 0;
   out_6973766442483655515[8] = 0;
   out_6973766442483655515[9] = 0;
   out_6973766442483655515[10] = 0;
   out_6973766442483655515[11] = 0;
   out_6973766442483655515[12] = 0;
   out_6973766442483655515[13] = 0;
   out_6973766442483655515[14] = 0;
   out_6973766442483655515[15] = 0;
   out_6973766442483655515[16] = 0;
   out_6973766442483655515[17] = 0;
   out_6973766442483655515[18] = 0;
   out_6973766442483655515[19] = 0;
   out_6973766442483655515[20] = 0;
   out_6973766442483655515[21] = 0;
   out_6973766442483655515[22] = 1;
   out_6973766442483655515[23] = 0;
   out_6973766442483655515[24] = 0;
   out_6973766442483655515[25] = 0;
   out_6973766442483655515[26] = 0;
   out_6973766442483655515[27] = 0;
   out_6973766442483655515[28] = 0;
   out_6973766442483655515[29] = 0;
   out_6973766442483655515[30] = 0;
   out_6973766442483655515[31] = 0;
   out_6973766442483655515[32] = 0;
   out_6973766442483655515[33] = 0;
   out_6973766442483655515[34] = 0;
   out_6973766442483655515[35] = 0;
   out_6973766442483655515[36] = 0;
   out_6973766442483655515[37] = 0;
   out_6973766442483655515[38] = 0;
   out_6973766442483655515[39] = 0;
   out_6973766442483655515[40] = 0;
   out_6973766442483655515[41] = 1;
   out_6973766442483655515[42] = 0;
   out_6973766442483655515[43] = 0;
   out_6973766442483655515[44] = 0;
   out_6973766442483655515[45] = 0;
   out_6973766442483655515[46] = 0;
   out_6973766442483655515[47] = 0;
   out_6973766442483655515[48] = 0;
   out_6973766442483655515[49] = 0;
   out_6973766442483655515[50] = 0;
   out_6973766442483655515[51] = 0;
   out_6973766442483655515[52] = 0;
   out_6973766442483655515[53] = 0;
}
void h_14(double *state, double *unused, double *out_1095581425659281568) {
   out_1095581425659281568[0] = state[6];
   out_1095581425659281568[1] = state[7];
   out_1095581425659281568[2] = state[8];
}
void H_14(double *state, double *unused, double *out_678704184855950418) {
   out_678704184855950418[0] = 0;
   out_678704184855950418[1] = 0;
   out_678704184855950418[2] = 0;
   out_678704184855950418[3] = 0;
   out_678704184855950418[4] = 0;
   out_678704184855950418[5] = 0;
   out_678704184855950418[6] = 1;
   out_678704184855950418[7] = 0;
   out_678704184855950418[8] = 0;
   out_678704184855950418[9] = 0;
   out_678704184855950418[10] = 0;
   out_678704184855950418[11] = 0;
   out_678704184855950418[12] = 0;
   out_678704184855950418[13] = 0;
   out_678704184855950418[14] = 0;
   out_678704184855950418[15] = 0;
   out_678704184855950418[16] = 0;
   out_678704184855950418[17] = 0;
   out_678704184855950418[18] = 0;
   out_678704184855950418[19] = 0;
   out_678704184855950418[20] = 0;
   out_678704184855950418[21] = 0;
   out_678704184855950418[22] = 0;
   out_678704184855950418[23] = 0;
   out_678704184855950418[24] = 0;
   out_678704184855950418[25] = 1;
   out_678704184855950418[26] = 0;
   out_678704184855950418[27] = 0;
   out_678704184855950418[28] = 0;
   out_678704184855950418[29] = 0;
   out_678704184855950418[30] = 0;
   out_678704184855950418[31] = 0;
   out_678704184855950418[32] = 0;
   out_678704184855950418[33] = 0;
   out_678704184855950418[34] = 0;
   out_678704184855950418[35] = 0;
   out_678704184855950418[36] = 0;
   out_678704184855950418[37] = 0;
   out_678704184855950418[38] = 0;
   out_678704184855950418[39] = 0;
   out_678704184855950418[40] = 0;
   out_678704184855950418[41] = 0;
   out_678704184855950418[42] = 0;
   out_678704184855950418[43] = 0;
   out_678704184855950418[44] = 1;
   out_678704184855950418[45] = 0;
   out_678704184855950418[46] = 0;
   out_678704184855950418[47] = 0;
   out_678704184855950418[48] = 0;
   out_678704184855950418[49] = 0;
   out_678704184855950418[50] = 0;
   out_678704184855950418[51] = 0;
   out_678704184855950418[52] = 0;
   out_678704184855950418[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_8958383251573640) {
  err_fun(nom_x, delta_x, out_8958383251573640);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3510167321874192836) {
  inv_err_fun(nom_x, true_x, out_3510167321874192836);
}
void pose_H_mod_fun(double *state, double *out_10314592692584858) {
  H_mod_fun(state, out_10314592692584858);
}
void pose_f_fun(double *state, double dt, double *out_3469176563342886468) {
  f_fun(state,  dt, out_3469176563342886468);
}
void pose_F_fun(double *state, double dt, double *out_6053143964145098388) {
  F_fun(state,  dt, out_6053143964145098388);
}
void pose_h_4(double *state, double *unused, double *out_4331217932147478278) {
  h_4(state, unused, out_4331217932147478278);
}
void pose_H_4(double *state, double *unused, double *out_3761492617151322714) {
  H_4(state, unused, out_3761492617151322714);
}
void pose_h_10(double *state, double *unused, double *out_1904703987337421912) {
  h_10(state, unused, out_1904703987337421912);
}
void pose_H_10(double *state, double *unused, double *out_4366147958481579120) {
  H_10(state, unused, out_4366147958481579120);
}
void pose_h_13(double *state, double *unused, double *out_9149454562438237975) {
  h_13(state, unused, out_9149454562438237975);
}
void pose_H_13(double *state, double *unused, double *out_6973766442483655515) {
  H_13(state, unused, out_6973766442483655515);
}
void pose_h_14(double *state, double *unused, double *out_1095581425659281568) {
  h_14(state, unused, out_1095581425659281568);
}
void pose_H_14(double *state, double *unused, double *out_678704184855950418) {
  H_14(state, unused, out_678704184855950418);
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
