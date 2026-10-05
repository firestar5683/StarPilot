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
void err_fun(double *nom_x, double *delta_x, double *out_5541167196451846312) {
   out_5541167196451846312[0] = delta_x[0] + nom_x[0];
   out_5541167196451846312[1] = delta_x[1] + nom_x[1];
   out_5541167196451846312[2] = delta_x[2] + nom_x[2];
   out_5541167196451846312[3] = delta_x[3] + nom_x[3];
   out_5541167196451846312[4] = delta_x[4] + nom_x[4];
   out_5541167196451846312[5] = delta_x[5] + nom_x[5];
   out_5541167196451846312[6] = delta_x[6] + nom_x[6];
   out_5541167196451846312[7] = delta_x[7] + nom_x[7];
   out_5541167196451846312[8] = delta_x[8] + nom_x[8];
   out_5541167196451846312[9] = delta_x[9] + nom_x[9];
   out_5541167196451846312[10] = delta_x[10] + nom_x[10];
   out_5541167196451846312[11] = delta_x[11] + nom_x[11];
   out_5541167196451846312[12] = delta_x[12] + nom_x[12];
   out_5541167196451846312[13] = delta_x[13] + nom_x[13];
   out_5541167196451846312[14] = delta_x[14] + nom_x[14];
   out_5541167196451846312[15] = delta_x[15] + nom_x[15];
   out_5541167196451846312[16] = delta_x[16] + nom_x[16];
   out_5541167196451846312[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_497075597603097975) {
   out_497075597603097975[0] = -nom_x[0] + true_x[0];
   out_497075597603097975[1] = -nom_x[1] + true_x[1];
   out_497075597603097975[2] = -nom_x[2] + true_x[2];
   out_497075597603097975[3] = -nom_x[3] + true_x[3];
   out_497075597603097975[4] = -nom_x[4] + true_x[4];
   out_497075597603097975[5] = -nom_x[5] + true_x[5];
   out_497075597603097975[6] = -nom_x[6] + true_x[6];
   out_497075597603097975[7] = -nom_x[7] + true_x[7];
   out_497075597603097975[8] = -nom_x[8] + true_x[8];
   out_497075597603097975[9] = -nom_x[9] + true_x[9];
   out_497075597603097975[10] = -nom_x[10] + true_x[10];
   out_497075597603097975[11] = -nom_x[11] + true_x[11];
   out_497075597603097975[12] = -nom_x[12] + true_x[12];
   out_497075597603097975[13] = -nom_x[13] + true_x[13];
   out_497075597603097975[14] = -nom_x[14] + true_x[14];
   out_497075597603097975[15] = -nom_x[15] + true_x[15];
   out_497075597603097975[16] = -nom_x[16] + true_x[16];
   out_497075597603097975[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_724419807350783906) {
   out_724419807350783906[0] = 1.0;
   out_724419807350783906[1] = 0.0;
   out_724419807350783906[2] = 0.0;
   out_724419807350783906[3] = 0.0;
   out_724419807350783906[4] = 0.0;
   out_724419807350783906[5] = 0.0;
   out_724419807350783906[6] = 0.0;
   out_724419807350783906[7] = 0.0;
   out_724419807350783906[8] = 0.0;
   out_724419807350783906[9] = 0.0;
   out_724419807350783906[10] = 0.0;
   out_724419807350783906[11] = 0.0;
   out_724419807350783906[12] = 0.0;
   out_724419807350783906[13] = 0.0;
   out_724419807350783906[14] = 0.0;
   out_724419807350783906[15] = 0.0;
   out_724419807350783906[16] = 0.0;
   out_724419807350783906[17] = 0.0;
   out_724419807350783906[18] = 0.0;
   out_724419807350783906[19] = 1.0;
   out_724419807350783906[20] = 0.0;
   out_724419807350783906[21] = 0.0;
   out_724419807350783906[22] = 0.0;
   out_724419807350783906[23] = 0.0;
   out_724419807350783906[24] = 0.0;
   out_724419807350783906[25] = 0.0;
   out_724419807350783906[26] = 0.0;
   out_724419807350783906[27] = 0.0;
   out_724419807350783906[28] = 0.0;
   out_724419807350783906[29] = 0.0;
   out_724419807350783906[30] = 0.0;
   out_724419807350783906[31] = 0.0;
   out_724419807350783906[32] = 0.0;
   out_724419807350783906[33] = 0.0;
   out_724419807350783906[34] = 0.0;
   out_724419807350783906[35] = 0.0;
   out_724419807350783906[36] = 0.0;
   out_724419807350783906[37] = 0.0;
   out_724419807350783906[38] = 1.0;
   out_724419807350783906[39] = 0.0;
   out_724419807350783906[40] = 0.0;
   out_724419807350783906[41] = 0.0;
   out_724419807350783906[42] = 0.0;
   out_724419807350783906[43] = 0.0;
   out_724419807350783906[44] = 0.0;
   out_724419807350783906[45] = 0.0;
   out_724419807350783906[46] = 0.0;
   out_724419807350783906[47] = 0.0;
   out_724419807350783906[48] = 0.0;
   out_724419807350783906[49] = 0.0;
   out_724419807350783906[50] = 0.0;
   out_724419807350783906[51] = 0.0;
   out_724419807350783906[52] = 0.0;
   out_724419807350783906[53] = 0.0;
   out_724419807350783906[54] = 0.0;
   out_724419807350783906[55] = 0.0;
   out_724419807350783906[56] = 0.0;
   out_724419807350783906[57] = 1.0;
   out_724419807350783906[58] = 0.0;
   out_724419807350783906[59] = 0.0;
   out_724419807350783906[60] = 0.0;
   out_724419807350783906[61] = 0.0;
   out_724419807350783906[62] = 0.0;
   out_724419807350783906[63] = 0.0;
   out_724419807350783906[64] = 0.0;
   out_724419807350783906[65] = 0.0;
   out_724419807350783906[66] = 0.0;
   out_724419807350783906[67] = 0.0;
   out_724419807350783906[68] = 0.0;
   out_724419807350783906[69] = 0.0;
   out_724419807350783906[70] = 0.0;
   out_724419807350783906[71] = 0.0;
   out_724419807350783906[72] = 0.0;
   out_724419807350783906[73] = 0.0;
   out_724419807350783906[74] = 0.0;
   out_724419807350783906[75] = 0.0;
   out_724419807350783906[76] = 1.0;
   out_724419807350783906[77] = 0.0;
   out_724419807350783906[78] = 0.0;
   out_724419807350783906[79] = 0.0;
   out_724419807350783906[80] = 0.0;
   out_724419807350783906[81] = 0.0;
   out_724419807350783906[82] = 0.0;
   out_724419807350783906[83] = 0.0;
   out_724419807350783906[84] = 0.0;
   out_724419807350783906[85] = 0.0;
   out_724419807350783906[86] = 0.0;
   out_724419807350783906[87] = 0.0;
   out_724419807350783906[88] = 0.0;
   out_724419807350783906[89] = 0.0;
   out_724419807350783906[90] = 0.0;
   out_724419807350783906[91] = 0.0;
   out_724419807350783906[92] = 0.0;
   out_724419807350783906[93] = 0.0;
   out_724419807350783906[94] = 0.0;
   out_724419807350783906[95] = 1.0;
   out_724419807350783906[96] = 0.0;
   out_724419807350783906[97] = 0.0;
   out_724419807350783906[98] = 0.0;
   out_724419807350783906[99] = 0.0;
   out_724419807350783906[100] = 0.0;
   out_724419807350783906[101] = 0.0;
   out_724419807350783906[102] = 0.0;
   out_724419807350783906[103] = 0.0;
   out_724419807350783906[104] = 0.0;
   out_724419807350783906[105] = 0.0;
   out_724419807350783906[106] = 0.0;
   out_724419807350783906[107] = 0.0;
   out_724419807350783906[108] = 0.0;
   out_724419807350783906[109] = 0.0;
   out_724419807350783906[110] = 0.0;
   out_724419807350783906[111] = 0.0;
   out_724419807350783906[112] = 0.0;
   out_724419807350783906[113] = 0.0;
   out_724419807350783906[114] = 1.0;
   out_724419807350783906[115] = 0.0;
   out_724419807350783906[116] = 0.0;
   out_724419807350783906[117] = 0.0;
   out_724419807350783906[118] = 0.0;
   out_724419807350783906[119] = 0.0;
   out_724419807350783906[120] = 0.0;
   out_724419807350783906[121] = 0.0;
   out_724419807350783906[122] = 0.0;
   out_724419807350783906[123] = 0.0;
   out_724419807350783906[124] = 0.0;
   out_724419807350783906[125] = 0.0;
   out_724419807350783906[126] = 0.0;
   out_724419807350783906[127] = 0.0;
   out_724419807350783906[128] = 0.0;
   out_724419807350783906[129] = 0.0;
   out_724419807350783906[130] = 0.0;
   out_724419807350783906[131] = 0.0;
   out_724419807350783906[132] = 0.0;
   out_724419807350783906[133] = 1.0;
   out_724419807350783906[134] = 0.0;
   out_724419807350783906[135] = 0.0;
   out_724419807350783906[136] = 0.0;
   out_724419807350783906[137] = 0.0;
   out_724419807350783906[138] = 0.0;
   out_724419807350783906[139] = 0.0;
   out_724419807350783906[140] = 0.0;
   out_724419807350783906[141] = 0.0;
   out_724419807350783906[142] = 0.0;
   out_724419807350783906[143] = 0.0;
   out_724419807350783906[144] = 0.0;
   out_724419807350783906[145] = 0.0;
   out_724419807350783906[146] = 0.0;
   out_724419807350783906[147] = 0.0;
   out_724419807350783906[148] = 0.0;
   out_724419807350783906[149] = 0.0;
   out_724419807350783906[150] = 0.0;
   out_724419807350783906[151] = 0.0;
   out_724419807350783906[152] = 1.0;
   out_724419807350783906[153] = 0.0;
   out_724419807350783906[154] = 0.0;
   out_724419807350783906[155] = 0.0;
   out_724419807350783906[156] = 0.0;
   out_724419807350783906[157] = 0.0;
   out_724419807350783906[158] = 0.0;
   out_724419807350783906[159] = 0.0;
   out_724419807350783906[160] = 0.0;
   out_724419807350783906[161] = 0.0;
   out_724419807350783906[162] = 0.0;
   out_724419807350783906[163] = 0.0;
   out_724419807350783906[164] = 0.0;
   out_724419807350783906[165] = 0.0;
   out_724419807350783906[166] = 0.0;
   out_724419807350783906[167] = 0.0;
   out_724419807350783906[168] = 0.0;
   out_724419807350783906[169] = 0.0;
   out_724419807350783906[170] = 0.0;
   out_724419807350783906[171] = 1.0;
   out_724419807350783906[172] = 0.0;
   out_724419807350783906[173] = 0.0;
   out_724419807350783906[174] = 0.0;
   out_724419807350783906[175] = 0.0;
   out_724419807350783906[176] = 0.0;
   out_724419807350783906[177] = 0.0;
   out_724419807350783906[178] = 0.0;
   out_724419807350783906[179] = 0.0;
   out_724419807350783906[180] = 0.0;
   out_724419807350783906[181] = 0.0;
   out_724419807350783906[182] = 0.0;
   out_724419807350783906[183] = 0.0;
   out_724419807350783906[184] = 0.0;
   out_724419807350783906[185] = 0.0;
   out_724419807350783906[186] = 0.0;
   out_724419807350783906[187] = 0.0;
   out_724419807350783906[188] = 0.0;
   out_724419807350783906[189] = 0.0;
   out_724419807350783906[190] = 1.0;
   out_724419807350783906[191] = 0.0;
   out_724419807350783906[192] = 0.0;
   out_724419807350783906[193] = 0.0;
   out_724419807350783906[194] = 0.0;
   out_724419807350783906[195] = 0.0;
   out_724419807350783906[196] = 0.0;
   out_724419807350783906[197] = 0.0;
   out_724419807350783906[198] = 0.0;
   out_724419807350783906[199] = 0.0;
   out_724419807350783906[200] = 0.0;
   out_724419807350783906[201] = 0.0;
   out_724419807350783906[202] = 0.0;
   out_724419807350783906[203] = 0.0;
   out_724419807350783906[204] = 0.0;
   out_724419807350783906[205] = 0.0;
   out_724419807350783906[206] = 0.0;
   out_724419807350783906[207] = 0.0;
   out_724419807350783906[208] = 0.0;
   out_724419807350783906[209] = 1.0;
   out_724419807350783906[210] = 0.0;
   out_724419807350783906[211] = 0.0;
   out_724419807350783906[212] = 0.0;
   out_724419807350783906[213] = 0.0;
   out_724419807350783906[214] = 0.0;
   out_724419807350783906[215] = 0.0;
   out_724419807350783906[216] = 0.0;
   out_724419807350783906[217] = 0.0;
   out_724419807350783906[218] = 0.0;
   out_724419807350783906[219] = 0.0;
   out_724419807350783906[220] = 0.0;
   out_724419807350783906[221] = 0.0;
   out_724419807350783906[222] = 0.0;
   out_724419807350783906[223] = 0.0;
   out_724419807350783906[224] = 0.0;
   out_724419807350783906[225] = 0.0;
   out_724419807350783906[226] = 0.0;
   out_724419807350783906[227] = 0.0;
   out_724419807350783906[228] = 1.0;
   out_724419807350783906[229] = 0.0;
   out_724419807350783906[230] = 0.0;
   out_724419807350783906[231] = 0.0;
   out_724419807350783906[232] = 0.0;
   out_724419807350783906[233] = 0.0;
   out_724419807350783906[234] = 0.0;
   out_724419807350783906[235] = 0.0;
   out_724419807350783906[236] = 0.0;
   out_724419807350783906[237] = 0.0;
   out_724419807350783906[238] = 0.0;
   out_724419807350783906[239] = 0.0;
   out_724419807350783906[240] = 0.0;
   out_724419807350783906[241] = 0.0;
   out_724419807350783906[242] = 0.0;
   out_724419807350783906[243] = 0.0;
   out_724419807350783906[244] = 0.0;
   out_724419807350783906[245] = 0.0;
   out_724419807350783906[246] = 0.0;
   out_724419807350783906[247] = 1.0;
   out_724419807350783906[248] = 0.0;
   out_724419807350783906[249] = 0.0;
   out_724419807350783906[250] = 0.0;
   out_724419807350783906[251] = 0.0;
   out_724419807350783906[252] = 0.0;
   out_724419807350783906[253] = 0.0;
   out_724419807350783906[254] = 0.0;
   out_724419807350783906[255] = 0.0;
   out_724419807350783906[256] = 0.0;
   out_724419807350783906[257] = 0.0;
   out_724419807350783906[258] = 0.0;
   out_724419807350783906[259] = 0.0;
   out_724419807350783906[260] = 0.0;
   out_724419807350783906[261] = 0.0;
   out_724419807350783906[262] = 0.0;
   out_724419807350783906[263] = 0.0;
   out_724419807350783906[264] = 0.0;
   out_724419807350783906[265] = 0.0;
   out_724419807350783906[266] = 1.0;
   out_724419807350783906[267] = 0.0;
   out_724419807350783906[268] = 0.0;
   out_724419807350783906[269] = 0.0;
   out_724419807350783906[270] = 0.0;
   out_724419807350783906[271] = 0.0;
   out_724419807350783906[272] = 0.0;
   out_724419807350783906[273] = 0.0;
   out_724419807350783906[274] = 0.0;
   out_724419807350783906[275] = 0.0;
   out_724419807350783906[276] = 0.0;
   out_724419807350783906[277] = 0.0;
   out_724419807350783906[278] = 0.0;
   out_724419807350783906[279] = 0.0;
   out_724419807350783906[280] = 0.0;
   out_724419807350783906[281] = 0.0;
   out_724419807350783906[282] = 0.0;
   out_724419807350783906[283] = 0.0;
   out_724419807350783906[284] = 0.0;
   out_724419807350783906[285] = 1.0;
   out_724419807350783906[286] = 0.0;
   out_724419807350783906[287] = 0.0;
   out_724419807350783906[288] = 0.0;
   out_724419807350783906[289] = 0.0;
   out_724419807350783906[290] = 0.0;
   out_724419807350783906[291] = 0.0;
   out_724419807350783906[292] = 0.0;
   out_724419807350783906[293] = 0.0;
   out_724419807350783906[294] = 0.0;
   out_724419807350783906[295] = 0.0;
   out_724419807350783906[296] = 0.0;
   out_724419807350783906[297] = 0.0;
   out_724419807350783906[298] = 0.0;
   out_724419807350783906[299] = 0.0;
   out_724419807350783906[300] = 0.0;
   out_724419807350783906[301] = 0.0;
   out_724419807350783906[302] = 0.0;
   out_724419807350783906[303] = 0.0;
   out_724419807350783906[304] = 1.0;
   out_724419807350783906[305] = 0.0;
   out_724419807350783906[306] = 0.0;
   out_724419807350783906[307] = 0.0;
   out_724419807350783906[308] = 0.0;
   out_724419807350783906[309] = 0.0;
   out_724419807350783906[310] = 0.0;
   out_724419807350783906[311] = 0.0;
   out_724419807350783906[312] = 0.0;
   out_724419807350783906[313] = 0.0;
   out_724419807350783906[314] = 0.0;
   out_724419807350783906[315] = 0.0;
   out_724419807350783906[316] = 0.0;
   out_724419807350783906[317] = 0.0;
   out_724419807350783906[318] = 0.0;
   out_724419807350783906[319] = 0.0;
   out_724419807350783906[320] = 0.0;
   out_724419807350783906[321] = 0.0;
   out_724419807350783906[322] = 0.0;
   out_724419807350783906[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_6691116852918071868) {
   out_6691116852918071868[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_6691116852918071868[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_6691116852918071868[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_6691116852918071868[3] = dt*state[12] + state[3];
   out_6691116852918071868[4] = dt*state[13] + state[4];
   out_6691116852918071868[5] = dt*state[14] + state[5];
   out_6691116852918071868[6] = state[6];
   out_6691116852918071868[7] = state[7];
   out_6691116852918071868[8] = state[8];
   out_6691116852918071868[9] = state[9];
   out_6691116852918071868[10] = state[10];
   out_6691116852918071868[11] = state[11];
   out_6691116852918071868[12] = state[12];
   out_6691116852918071868[13] = state[13];
   out_6691116852918071868[14] = state[14];
   out_6691116852918071868[15] = state[15];
   out_6691116852918071868[16] = state[16];
   out_6691116852918071868[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3096830296170468775) {
   out_3096830296170468775[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3096830296170468775[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3096830296170468775[2] = 0;
   out_3096830296170468775[3] = 0;
   out_3096830296170468775[4] = 0;
   out_3096830296170468775[5] = 0;
   out_3096830296170468775[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3096830296170468775[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3096830296170468775[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3096830296170468775[9] = 0;
   out_3096830296170468775[10] = 0;
   out_3096830296170468775[11] = 0;
   out_3096830296170468775[12] = 0;
   out_3096830296170468775[13] = 0;
   out_3096830296170468775[14] = 0;
   out_3096830296170468775[15] = 0;
   out_3096830296170468775[16] = 0;
   out_3096830296170468775[17] = 0;
   out_3096830296170468775[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3096830296170468775[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3096830296170468775[20] = 0;
   out_3096830296170468775[21] = 0;
   out_3096830296170468775[22] = 0;
   out_3096830296170468775[23] = 0;
   out_3096830296170468775[24] = 0;
   out_3096830296170468775[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3096830296170468775[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3096830296170468775[27] = 0;
   out_3096830296170468775[28] = 0;
   out_3096830296170468775[29] = 0;
   out_3096830296170468775[30] = 0;
   out_3096830296170468775[31] = 0;
   out_3096830296170468775[32] = 0;
   out_3096830296170468775[33] = 0;
   out_3096830296170468775[34] = 0;
   out_3096830296170468775[35] = 0;
   out_3096830296170468775[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3096830296170468775[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3096830296170468775[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3096830296170468775[39] = 0;
   out_3096830296170468775[40] = 0;
   out_3096830296170468775[41] = 0;
   out_3096830296170468775[42] = 0;
   out_3096830296170468775[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3096830296170468775[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3096830296170468775[45] = 0;
   out_3096830296170468775[46] = 0;
   out_3096830296170468775[47] = 0;
   out_3096830296170468775[48] = 0;
   out_3096830296170468775[49] = 0;
   out_3096830296170468775[50] = 0;
   out_3096830296170468775[51] = 0;
   out_3096830296170468775[52] = 0;
   out_3096830296170468775[53] = 0;
   out_3096830296170468775[54] = 0;
   out_3096830296170468775[55] = 0;
   out_3096830296170468775[56] = 0;
   out_3096830296170468775[57] = 1;
   out_3096830296170468775[58] = 0;
   out_3096830296170468775[59] = 0;
   out_3096830296170468775[60] = 0;
   out_3096830296170468775[61] = 0;
   out_3096830296170468775[62] = 0;
   out_3096830296170468775[63] = 0;
   out_3096830296170468775[64] = 0;
   out_3096830296170468775[65] = 0;
   out_3096830296170468775[66] = dt;
   out_3096830296170468775[67] = 0;
   out_3096830296170468775[68] = 0;
   out_3096830296170468775[69] = 0;
   out_3096830296170468775[70] = 0;
   out_3096830296170468775[71] = 0;
   out_3096830296170468775[72] = 0;
   out_3096830296170468775[73] = 0;
   out_3096830296170468775[74] = 0;
   out_3096830296170468775[75] = 0;
   out_3096830296170468775[76] = 1;
   out_3096830296170468775[77] = 0;
   out_3096830296170468775[78] = 0;
   out_3096830296170468775[79] = 0;
   out_3096830296170468775[80] = 0;
   out_3096830296170468775[81] = 0;
   out_3096830296170468775[82] = 0;
   out_3096830296170468775[83] = 0;
   out_3096830296170468775[84] = 0;
   out_3096830296170468775[85] = dt;
   out_3096830296170468775[86] = 0;
   out_3096830296170468775[87] = 0;
   out_3096830296170468775[88] = 0;
   out_3096830296170468775[89] = 0;
   out_3096830296170468775[90] = 0;
   out_3096830296170468775[91] = 0;
   out_3096830296170468775[92] = 0;
   out_3096830296170468775[93] = 0;
   out_3096830296170468775[94] = 0;
   out_3096830296170468775[95] = 1;
   out_3096830296170468775[96] = 0;
   out_3096830296170468775[97] = 0;
   out_3096830296170468775[98] = 0;
   out_3096830296170468775[99] = 0;
   out_3096830296170468775[100] = 0;
   out_3096830296170468775[101] = 0;
   out_3096830296170468775[102] = 0;
   out_3096830296170468775[103] = 0;
   out_3096830296170468775[104] = dt;
   out_3096830296170468775[105] = 0;
   out_3096830296170468775[106] = 0;
   out_3096830296170468775[107] = 0;
   out_3096830296170468775[108] = 0;
   out_3096830296170468775[109] = 0;
   out_3096830296170468775[110] = 0;
   out_3096830296170468775[111] = 0;
   out_3096830296170468775[112] = 0;
   out_3096830296170468775[113] = 0;
   out_3096830296170468775[114] = 1;
   out_3096830296170468775[115] = 0;
   out_3096830296170468775[116] = 0;
   out_3096830296170468775[117] = 0;
   out_3096830296170468775[118] = 0;
   out_3096830296170468775[119] = 0;
   out_3096830296170468775[120] = 0;
   out_3096830296170468775[121] = 0;
   out_3096830296170468775[122] = 0;
   out_3096830296170468775[123] = 0;
   out_3096830296170468775[124] = 0;
   out_3096830296170468775[125] = 0;
   out_3096830296170468775[126] = 0;
   out_3096830296170468775[127] = 0;
   out_3096830296170468775[128] = 0;
   out_3096830296170468775[129] = 0;
   out_3096830296170468775[130] = 0;
   out_3096830296170468775[131] = 0;
   out_3096830296170468775[132] = 0;
   out_3096830296170468775[133] = 1;
   out_3096830296170468775[134] = 0;
   out_3096830296170468775[135] = 0;
   out_3096830296170468775[136] = 0;
   out_3096830296170468775[137] = 0;
   out_3096830296170468775[138] = 0;
   out_3096830296170468775[139] = 0;
   out_3096830296170468775[140] = 0;
   out_3096830296170468775[141] = 0;
   out_3096830296170468775[142] = 0;
   out_3096830296170468775[143] = 0;
   out_3096830296170468775[144] = 0;
   out_3096830296170468775[145] = 0;
   out_3096830296170468775[146] = 0;
   out_3096830296170468775[147] = 0;
   out_3096830296170468775[148] = 0;
   out_3096830296170468775[149] = 0;
   out_3096830296170468775[150] = 0;
   out_3096830296170468775[151] = 0;
   out_3096830296170468775[152] = 1;
   out_3096830296170468775[153] = 0;
   out_3096830296170468775[154] = 0;
   out_3096830296170468775[155] = 0;
   out_3096830296170468775[156] = 0;
   out_3096830296170468775[157] = 0;
   out_3096830296170468775[158] = 0;
   out_3096830296170468775[159] = 0;
   out_3096830296170468775[160] = 0;
   out_3096830296170468775[161] = 0;
   out_3096830296170468775[162] = 0;
   out_3096830296170468775[163] = 0;
   out_3096830296170468775[164] = 0;
   out_3096830296170468775[165] = 0;
   out_3096830296170468775[166] = 0;
   out_3096830296170468775[167] = 0;
   out_3096830296170468775[168] = 0;
   out_3096830296170468775[169] = 0;
   out_3096830296170468775[170] = 0;
   out_3096830296170468775[171] = 1;
   out_3096830296170468775[172] = 0;
   out_3096830296170468775[173] = 0;
   out_3096830296170468775[174] = 0;
   out_3096830296170468775[175] = 0;
   out_3096830296170468775[176] = 0;
   out_3096830296170468775[177] = 0;
   out_3096830296170468775[178] = 0;
   out_3096830296170468775[179] = 0;
   out_3096830296170468775[180] = 0;
   out_3096830296170468775[181] = 0;
   out_3096830296170468775[182] = 0;
   out_3096830296170468775[183] = 0;
   out_3096830296170468775[184] = 0;
   out_3096830296170468775[185] = 0;
   out_3096830296170468775[186] = 0;
   out_3096830296170468775[187] = 0;
   out_3096830296170468775[188] = 0;
   out_3096830296170468775[189] = 0;
   out_3096830296170468775[190] = 1;
   out_3096830296170468775[191] = 0;
   out_3096830296170468775[192] = 0;
   out_3096830296170468775[193] = 0;
   out_3096830296170468775[194] = 0;
   out_3096830296170468775[195] = 0;
   out_3096830296170468775[196] = 0;
   out_3096830296170468775[197] = 0;
   out_3096830296170468775[198] = 0;
   out_3096830296170468775[199] = 0;
   out_3096830296170468775[200] = 0;
   out_3096830296170468775[201] = 0;
   out_3096830296170468775[202] = 0;
   out_3096830296170468775[203] = 0;
   out_3096830296170468775[204] = 0;
   out_3096830296170468775[205] = 0;
   out_3096830296170468775[206] = 0;
   out_3096830296170468775[207] = 0;
   out_3096830296170468775[208] = 0;
   out_3096830296170468775[209] = 1;
   out_3096830296170468775[210] = 0;
   out_3096830296170468775[211] = 0;
   out_3096830296170468775[212] = 0;
   out_3096830296170468775[213] = 0;
   out_3096830296170468775[214] = 0;
   out_3096830296170468775[215] = 0;
   out_3096830296170468775[216] = 0;
   out_3096830296170468775[217] = 0;
   out_3096830296170468775[218] = 0;
   out_3096830296170468775[219] = 0;
   out_3096830296170468775[220] = 0;
   out_3096830296170468775[221] = 0;
   out_3096830296170468775[222] = 0;
   out_3096830296170468775[223] = 0;
   out_3096830296170468775[224] = 0;
   out_3096830296170468775[225] = 0;
   out_3096830296170468775[226] = 0;
   out_3096830296170468775[227] = 0;
   out_3096830296170468775[228] = 1;
   out_3096830296170468775[229] = 0;
   out_3096830296170468775[230] = 0;
   out_3096830296170468775[231] = 0;
   out_3096830296170468775[232] = 0;
   out_3096830296170468775[233] = 0;
   out_3096830296170468775[234] = 0;
   out_3096830296170468775[235] = 0;
   out_3096830296170468775[236] = 0;
   out_3096830296170468775[237] = 0;
   out_3096830296170468775[238] = 0;
   out_3096830296170468775[239] = 0;
   out_3096830296170468775[240] = 0;
   out_3096830296170468775[241] = 0;
   out_3096830296170468775[242] = 0;
   out_3096830296170468775[243] = 0;
   out_3096830296170468775[244] = 0;
   out_3096830296170468775[245] = 0;
   out_3096830296170468775[246] = 0;
   out_3096830296170468775[247] = 1;
   out_3096830296170468775[248] = 0;
   out_3096830296170468775[249] = 0;
   out_3096830296170468775[250] = 0;
   out_3096830296170468775[251] = 0;
   out_3096830296170468775[252] = 0;
   out_3096830296170468775[253] = 0;
   out_3096830296170468775[254] = 0;
   out_3096830296170468775[255] = 0;
   out_3096830296170468775[256] = 0;
   out_3096830296170468775[257] = 0;
   out_3096830296170468775[258] = 0;
   out_3096830296170468775[259] = 0;
   out_3096830296170468775[260] = 0;
   out_3096830296170468775[261] = 0;
   out_3096830296170468775[262] = 0;
   out_3096830296170468775[263] = 0;
   out_3096830296170468775[264] = 0;
   out_3096830296170468775[265] = 0;
   out_3096830296170468775[266] = 1;
   out_3096830296170468775[267] = 0;
   out_3096830296170468775[268] = 0;
   out_3096830296170468775[269] = 0;
   out_3096830296170468775[270] = 0;
   out_3096830296170468775[271] = 0;
   out_3096830296170468775[272] = 0;
   out_3096830296170468775[273] = 0;
   out_3096830296170468775[274] = 0;
   out_3096830296170468775[275] = 0;
   out_3096830296170468775[276] = 0;
   out_3096830296170468775[277] = 0;
   out_3096830296170468775[278] = 0;
   out_3096830296170468775[279] = 0;
   out_3096830296170468775[280] = 0;
   out_3096830296170468775[281] = 0;
   out_3096830296170468775[282] = 0;
   out_3096830296170468775[283] = 0;
   out_3096830296170468775[284] = 0;
   out_3096830296170468775[285] = 1;
   out_3096830296170468775[286] = 0;
   out_3096830296170468775[287] = 0;
   out_3096830296170468775[288] = 0;
   out_3096830296170468775[289] = 0;
   out_3096830296170468775[290] = 0;
   out_3096830296170468775[291] = 0;
   out_3096830296170468775[292] = 0;
   out_3096830296170468775[293] = 0;
   out_3096830296170468775[294] = 0;
   out_3096830296170468775[295] = 0;
   out_3096830296170468775[296] = 0;
   out_3096830296170468775[297] = 0;
   out_3096830296170468775[298] = 0;
   out_3096830296170468775[299] = 0;
   out_3096830296170468775[300] = 0;
   out_3096830296170468775[301] = 0;
   out_3096830296170468775[302] = 0;
   out_3096830296170468775[303] = 0;
   out_3096830296170468775[304] = 1;
   out_3096830296170468775[305] = 0;
   out_3096830296170468775[306] = 0;
   out_3096830296170468775[307] = 0;
   out_3096830296170468775[308] = 0;
   out_3096830296170468775[309] = 0;
   out_3096830296170468775[310] = 0;
   out_3096830296170468775[311] = 0;
   out_3096830296170468775[312] = 0;
   out_3096830296170468775[313] = 0;
   out_3096830296170468775[314] = 0;
   out_3096830296170468775[315] = 0;
   out_3096830296170468775[316] = 0;
   out_3096830296170468775[317] = 0;
   out_3096830296170468775[318] = 0;
   out_3096830296170468775[319] = 0;
   out_3096830296170468775[320] = 0;
   out_3096830296170468775[321] = 0;
   out_3096830296170468775[322] = 0;
   out_3096830296170468775[323] = 1;
}
void h_4(double *state, double *unused, double *out_9106257316383440258) {
   out_9106257316383440258[0] = state[6] + state[9];
   out_9106257316383440258[1] = state[7] + state[10];
   out_9106257316383440258[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8219941858707037436) {
   out_8219941858707037436[0] = 0;
   out_8219941858707037436[1] = 0;
   out_8219941858707037436[2] = 0;
   out_8219941858707037436[3] = 0;
   out_8219941858707037436[4] = 0;
   out_8219941858707037436[5] = 0;
   out_8219941858707037436[6] = 1;
   out_8219941858707037436[7] = 0;
   out_8219941858707037436[8] = 0;
   out_8219941858707037436[9] = 1;
   out_8219941858707037436[10] = 0;
   out_8219941858707037436[11] = 0;
   out_8219941858707037436[12] = 0;
   out_8219941858707037436[13] = 0;
   out_8219941858707037436[14] = 0;
   out_8219941858707037436[15] = 0;
   out_8219941858707037436[16] = 0;
   out_8219941858707037436[17] = 0;
   out_8219941858707037436[18] = 0;
   out_8219941858707037436[19] = 0;
   out_8219941858707037436[20] = 0;
   out_8219941858707037436[21] = 0;
   out_8219941858707037436[22] = 0;
   out_8219941858707037436[23] = 0;
   out_8219941858707037436[24] = 0;
   out_8219941858707037436[25] = 1;
   out_8219941858707037436[26] = 0;
   out_8219941858707037436[27] = 0;
   out_8219941858707037436[28] = 1;
   out_8219941858707037436[29] = 0;
   out_8219941858707037436[30] = 0;
   out_8219941858707037436[31] = 0;
   out_8219941858707037436[32] = 0;
   out_8219941858707037436[33] = 0;
   out_8219941858707037436[34] = 0;
   out_8219941858707037436[35] = 0;
   out_8219941858707037436[36] = 0;
   out_8219941858707037436[37] = 0;
   out_8219941858707037436[38] = 0;
   out_8219941858707037436[39] = 0;
   out_8219941858707037436[40] = 0;
   out_8219941858707037436[41] = 0;
   out_8219941858707037436[42] = 0;
   out_8219941858707037436[43] = 0;
   out_8219941858707037436[44] = 1;
   out_8219941858707037436[45] = 0;
   out_8219941858707037436[46] = 0;
   out_8219941858707037436[47] = 1;
   out_8219941858707037436[48] = 0;
   out_8219941858707037436[49] = 0;
   out_8219941858707037436[50] = 0;
   out_8219941858707037436[51] = 0;
   out_8219941858707037436[52] = 0;
   out_8219941858707037436[53] = 0;
}
void h_10(double *state, double *unused, double *out_423402028295143085) {
   out_423402028295143085[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_423402028295143085[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_423402028295143085[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3774900494247078646) {
   out_3774900494247078646[0] = 0;
   out_3774900494247078646[1] = 9.8100000000000005*cos(state[1]);
   out_3774900494247078646[2] = 0;
   out_3774900494247078646[3] = 0;
   out_3774900494247078646[4] = -state[8];
   out_3774900494247078646[5] = state[7];
   out_3774900494247078646[6] = 0;
   out_3774900494247078646[7] = state[5];
   out_3774900494247078646[8] = -state[4];
   out_3774900494247078646[9] = 0;
   out_3774900494247078646[10] = 0;
   out_3774900494247078646[11] = 0;
   out_3774900494247078646[12] = 1;
   out_3774900494247078646[13] = 0;
   out_3774900494247078646[14] = 0;
   out_3774900494247078646[15] = 1;
   out_3774900494247078646[16] = 0;
   out_3774900494247078646[17] = 0;
   out_3774900494247078646[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3774900494247078646[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3774900494247078646[20] = 0;
   out_3774900494247078646[21] = state[8];
   out_3774900494247078646[22] = 0;
   out_3774900494247078646[23] = -state[6];
   out_3774900494247078646[24] = -state[5];
   out_3774900494247078646[25] = 0;
   out_3774900494247078646[26] = state[3];
   out_3774900494247078646[27] = 0;
   out_3774900494247078646[28] = 0;
   out_3774900494247078646[29] = 0;
   out_3774900494247078646[30] = 0;
   out_3774900494247078646[31] = 1;
   out_3774900494247078646[32] = 0;
   out_3774900494247078646[33] = 0;
   out_3774900494247078646[34] = 1;
   out_3774900494247078646[35] = 0;
   out_3774900494247078646[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3774900494247078646[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3774900494247078646[38] = 0;
   out_3774900494247078646[39] = -state[7];
   out_3774900494247078646[40] = state[6];
   out_3774900494247078646[41] = 0;
   out_3774900494247078646[42] = state[4];
   out_3774900494247078646[43] = -state[3];
   out_3774900494247078646[44] = 0;
   out_3774900494247078646[45] = 0;
   out_3774900494247078646[46] = 0;
   out_3774900494247078646[47] = 0;
   out_3774900494247078646[48] = 0;
   out_3774900494247078646[49] = 0;
   out_3774900494247078646[50] = 1;
   out_3774900494247078646[51] = 0;
   out_3774900494247078646[52] = 0;
   out_3774900494247078646[53] = 1;
}
void h_13(double *state, double *unused, double *out_1499409244337466363) {
   out_1499409244337466363[0] = state[3];
   out_1499409244337466363[1] = state[4];
   out_1499409244337466363[2] = state[5];
}
void H_13(double *state, double *unused, double *out_5007668033374704635) {
   out_5007668033374704635[0] = 0;
   out_5007668033374704635[1] = 0;
   out_5007668033374704635[2] = 0;
   out_5007668033374704635[3] = 1;
   out_5007668033374704635[4] = 0;
   out_5007668033374704635[5] = 0;
   out_5007668033374704635[6] = 0;
   out_5007668033374704635[7] = 0;
   out_5007668033374704635[8] = 0;
   out_5007668033374704635[9] = 0;
   out_5007668033374704635[10] = 0;
   out_5007668033374704635[11] = 0;
   out_5007668033374704635[12] = 0;
   out_5007668033374704635[13] = 0;
   out_5007668033374704635[14] = 0;
   out_5007668033374704635[15] = 0;
   out_5007668033374704635[16] = 0;
   out_5007668033374704635[17] = 0;
   out_5007668033374704635[18] = 0;
   out_5007668033374704635[19] = 0;
   out_5007668033374704635[20] = 0;
   out_5007668033374704635[21] = 0;
   out_5007668033374704635[22] = 1;
   out_5007668033374704635[23] = 0;
   out_5007668033374704635[24] = 0;
   out_5007668033374704635[25] = 0;
   out_5007668033374704635[26] = 0;
   out_5007668033374704635[27] = 0;
   out_5007668033374704635[28] = 0;
   out_5007668033374704635[29] = 0;
   out_5007668033374704635[30] = 0;
   out_5007668033374704635[31] = 0;
   out_5007668033374704635[32] = 0;
   out_5007668033374704635[33] = 0;
   out_5007668033374704635[34] = 0;
   out_5007668033374704635[35] = 0;
   out_5007668033374704635[36] = 0;
   out_5007668033374704635[37] = 0;
   out_5007668033374704635[38] = 0;
   out_5007668033374704635[39] = 0;
   out_5007668033374704635[40] = 0;
   out_5007668033374704635[41] = 1;
   out_5007668033374704635[42] = 0;
   out_5007668033374704635[43] = 0;
   out_5007668033374704635[44] = 0;
   out_5007668033374704635[45] = 0;
   out_5007668033374704635[46] = 0;
   out_5007668033374704635[47] = 0;
   out_5007668033374704635[48] = 0;
   out_5007668033374704635[49] = 0;
   out_5007668033374704635[50] = 0;
   out_5007668033374704635[51] = 0;
   out_5007668033374704635[52] = 0;
   out_5007668033374704635[53] = 0;
}
void h_14(double *state, double *unused, double *out_7703910231150666575) {
   out_7703910231150666575[0] = state[6];
   out_7703910231150666575[1] = state[7];
   out_7703910231150666575[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4256701002367552907) {
   out_4256701002367552907[0] = 0;
   out_4256701002367552907[1] = 0;
   out_4256701002367552907[2] = 0;
   out_4256701002367552907[3] = 0;
   out_4256701002367552907[4] = 0;
   out_4256701002367552907[5] = 0;
   out_4256701002367552907[6] = 1;
   out_4256701002367552907[7] = 0;
   out_4256701002367552907[8] = 0;
   out_4256701002367552907[9] = 0;
   out_4256701002367552907[10] = 0;
   out_4256701002367552907[11] = 0;
   out_4256701002367552907[12] = 0;
   out_4256701002367552907[13] = 0;
   out_4256701002367552907[14] = 0;
   out_4256701002367552907[15] = 0;
   out_4256701002367552907[16] = 0;
   out_4256701002367552907[17] = 0;
   out_4256701002367552907[18] = 0;
   out_4256701002367552907[19] = 0;
   out_4256701002367552907[20] = 0;
   out_4256701002367552907[21] = 0;
   out_4256701002367552907[22] = 0;
   out_4256701002367552907[23] = 0;
   out_4256701002367552907[24] = 0;
   out_4256701002367552907[25] = 1;
   out_4256701002367552907[26] = 0;
   out_4256701002367552907[27] = 0;
   out_4256701002367552907[28] = 0;
   out_4256701002367552907[29] = 0;
   out_4256701002367552907[30] = 0;
   out_4256701002367552907[31] = 0;
   out_4256701002367552907[32] = 0;
   out_4256701002367552907[33] = 0;
   out_4256701002367552907[34] = 0;
   out_4256701002367552907[35] = 0;
   out_4256701002367552907[36] = 0;
   out_4256701002367552907[37] = 0;
   out_4256701002367552907[38] = 0;
   out_4256701002367552907[39] = 0;
   out_4256701002367552907[40] = 0;
   out_4256701002367552907[41] = 0;
   out_4256701002367552907[42] = 0;
   out_4256701002367552907[43] = 0;
   out_4256701002367552907[44] = 1;
   out_4256701002367552907[45] = 0;
   out_4256701002367552907[46] = 0;
   out_4256701002367552907[47] = 0;
   out_4256701002367552907[48] = 0;
   out_4256701002367552907[49] = 0;
   out_4256701002367552907[50] = 0;
   out_4256701002367552907[51] = 0;
   out_4256701002367552907[52] = 0;
   out_4256701002367552907[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5541167196451846312) {
  err_fun(nom_x, delta_x, out_5541167196451846312);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_497075597603097975) {
  inv_err_fun(nom_x, true_x, out_497075597603097975);
}
void pose_H_mod_fun(double *state, double *out_724419807350783906) {
  H_mod_fun(state, out_724419807350783906);
}
void pose_f_fun(double *state, double dt, double *out_6691116852918071868) {
  f_fun(state,  dt, out_6691116852918071868);
}
void pose_F_fun(double *state, double dt, double *out_3096830296170468775) {
  F_fun(state,  dt, out_3096830296170468775);
}
void pose_h_4(double *state, double *unused, double *out_9106257316383440258) {
  h_4(state, unused, out_9106257316383440258);
}
void pose_H_4(double *state, double *unused, double *out_8219941858707037436) {
  H_4(state, unused, out_8219941858707037436);
}
void pose_h_10(double *state, double *unused, double *out_423402028295143085) {
  h_10(state, unused, out_423402028295143085);
}
void pose_H_10(double *state, double *unused, double *out_3774900494247078646) {
  H_10(state, unused, out_3774900494247078646);
}
void pose_h_13(double *state, double *unused, double *out_1499409244337466363) {
  h_13(state, unused, out_1499409244337466363);
}
void pose_H_13(double *state, double *unused, double *out_5007668033374704635) {
  H_13(state, unused, out_5007668033374704635);
}
void pose_h_14(double *state, double *unused, double *out_7703910231150666575) {
  h_14(state, unused, out_7703910231150666575);
}
void pose_H_14(double *state, double *unused, double *out_4256701002367552907) {
  H_14(state, unused, out_4256701002367552907);
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
